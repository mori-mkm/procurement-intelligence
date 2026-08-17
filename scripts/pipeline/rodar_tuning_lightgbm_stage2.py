"""
Fase 13.12.2 - LightGBM tuning: regularizacao e learning rate.

Resultado do Stage 1:
    num_leaves = 63
    min_child_samples = 10

Objetivo desta etapa:
- manter complexidade da arvore congelada;
- variar somente learning_rate, reg_alpha e reg_lambda;
- treino exclusivamente em 2024;
- tuning exclusivamente em 2025;
- criterio primario: MAE no log do preco;
- 2026 permanece intocado.
"""

import json
import sys
from pathlib import Path

import pandas as pd
from lightgbm import (
    LGBMRegressor,
    early_stopping,
)


def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()

    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai

    raise RuntimeError("Nao encontrei a raiz do projeto")


RAIZ = achar_raiz_projeto(Path(__file__))
sys.path.insert(0, str(RAIZ))

OUTPUT_DIR = RAIZ / "data" / "model_validation"


from src.transformation.gold import load_gold_layer
from src.analytics.price_baseline import (
    prepare_baseline_dataset,
    split_temporal,
)
from src.analytics.price_ml import (
    FEATURES_CATEGORICAS,
    FEATURES_NUMERICAS,
    engineer_features,
    align_categorical_dtypes,
)
from src.analytics.model_selection import (
    build_prediction_errors,
    evaluate_prediction_errors,
)


FEATURES = (
    FEATURES_CATEGORICAS
    + FEATURES_NUMERICAS
)


# -------------------------------------------------------------
# Stage 1 congelou:
#     num_leaves = 63
#     min_child_samples = 10
#
# Stage 2 varia apenas learning rate e regularizacao.
# Grid pequeno, definido antes de observar os resultados.
# -------------------------------------------------------------
CANDIDATOS = [
    {
        "nome": "LR05_A0_L0",
        "learning_rate": 0.05,
        "reg_alpha": 0.0,
        "reg_lambda": 0.0,
    },
    {
        "nome": "LR05_A01_L0",
        "learning_rate": 0.05,
        "reg_alpha": 0.1,
        "reg_lambda": 0.0,
    },
    {
        "nome": "LR05_A0_L01",
        "learning_rate": 0.05,
        "reg_alpha": 0.0,
        "reg_lambda": 0.1,
    },
    {
        "nome": "LR05_A01_L01",
        "learning_rate": 0.05,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
    },
    {
        "nome": "LR05_A1_L1",
        "learning_rate": 0.05,
        "reg_alpha": 1.0,
        "reg_lambda": 1.0,
    },
    {
        "nome": "LR03_A0_L0",
        "learning_rate": 0.03,
        "reg_alpha": 0.0,
        "reg_lambda": 0.0,
    },
    {
        "nome": "LR03_A01_L01",
        "learning_rate": 0.03,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
    },
    {
        "nome": "LR03_A1_L1",
        "learning_rate": 0.03,
        "reg_alpha": 1.0,
        "reg_lambda": 1.0,
    },
]


def carregar_mae_v0():
    caminho = (
        OUTPUT_DIR
        / "lightgbm_v0_validation_2025_metrics.json"
    )

    if not caminho.exists():
        raise FileNotFoundError(
            "Metricas do LightGBM v0 nao encontradas: "
            f"{caminho}"
        )

    with caminho.open(
        "r",
        encoding="utf-8",
    ) as f:
        metrics = json.load(f)

    return float(metrics["mae_log"])


def main():
    print("=" * 85)
    print("FASE 13.12.2 - LIGHTGBM TUNING | REGULARIZACAO")
    print("=" * 85)

    # ---------------------------------------------------------
    # 1. Gold
    # ---------------------------------------------------------
    print("\n[1/6] Carregando Gold...")

    gold = load_gold_layer()
    fact = gold["fact_purchase"]

    print(
        f"Fact purchase: {len(fact):,} linhas"
    )

    # ---------------------------------------------------------
    # 2. Populacao oficial limpa
    # ---------------------------------------------------------
    print("\n[2/6] Preparando dataset...")

    df = prepare_baseline_dataset(fact)
    df = engineer_features(df)

    print(
        f"Dataset apos filtros: {len(df):,} linhas"
    )

    # ---------------------------------------------------------
    # 3. Split temporal
    # ---------------------------------------------------------
    print("\n[3/6] Aplicando split temporal...")

    splits = split_temporal(df)

    treino_raw = splits["treino"].copy()
    validacao_raw = splits["validacao"].copy()

    print(
        f"Treino 2024:     {len(treino_raw):,}"
    )

    print(
        f"Validacao 2025: {len(validacao_raw):,}"
    )

    print(
        "\nIMPORTANTE: 2026 nao sera avaliado."
    )

    # ---------------------------------------------------------
    # 4. Features
    # ---------------------------------------------------------
    print("\n[4/6] Preparando features...")

    treino, validacao = align_categorical_dtypes(
        treino_raw.copy(),
        validacao_raw.copy(),
    )

    X_train = treino[FEATURES]
    y_train = treino["log_unit_price"].astype(float)

    X_valid = validacao[FEATURES]
    y_valid = validacao["log_unit_price"].astype(float)

    train_item_keys = (
        treino_raw["item_key"]
        .dropna()
        .unique()
    )

    # ---------------------------------------------------------
    # 5. Tuning
    # ---------------------------------------------------------
    print("\n[5/6] Avaliando candidatos...")

    mae_v0 = carregar_mae_v0()

    print(
        f"\nLightGBM v0 MAE log: {mae_v0:.6f}"
    )

    resultados = []

    melhor_mae = float("inf")
    melhor_errors = None
    melhor_nome = None

    for i, candidato in enumerate(
        CANDIDATOS,
        start=1,
    ):
        print("\n" + "-" * 85)

        print(
            f"[{i}/{len(CANDIDATOS)}] "
            f"{candidato['nome']}"
        )

        print(
            f"learning_rate="
            f"{candidato['learning_rate']} | "
            f"reg_alpha="
            f"{candidato['reg_alpha']} | "
            f"reg_lambda="
            f"{candidato['reg_lambda']}"
        )

        modelo = LGBMRegressor(
            objective="regression",
            metric="l1",

            n_estimators=2000,

            learning_rate=candidato[
                "learning_rate"
            ],

            num_leaves=63,
            min_child_samples=10,

            reg_alpha=candidato[
                "reg_alpha"
            ],

            reg_lambda=candidato[
                "reg_lambda"
            ],

            random_state=42,
            n_jobs=-1,
            verbosity=-1,
        )

        # LightGBM 4.7:
        # eval_X / eval_y substituem o eval_set depreciado.
        modelo.fit(
            X_train,
            y_train,

            eval_X=X_valid,
            eval_y=y_valid,

            callbacks=[
                early_stopping(
                    stopping_rounds=75,
                    first_metric_only=True,
                    verbose=False,
                )
            ],
        )

        best_iteration = int(
            modelo.best_iteration_
        )

        log_pred = modelo.predict(
            X_valid,
            num_iteration=best_iteration,
        )

        errors = build_prediction_errors(
            df=validacao_raw,
            log_pred=log_pred,
            model_name=candidato["nome"],
            train_item_keys=train_item_keys,
        )

        metrics = evaluate_prediction_errors(
            errors
        )

        melhoria_vs_v0 = (
            100
            * (
                mae_v0
                - metrics["mae_log"]
            )
            / mae_v0
        )

        resultado = {
            "nome": candidato["nome"],

            "num_leaves": 63,
            "min_child_samples": 10,

            "learning_rate": candidato[
                "learning_rate"
            ],

            "reg_alpha": candidato[
                "reg_alpha"
            ],

            "reg_lambda": candidato[
                "reg_lambda"
            ],

            "best_iteration": best_iteration,

            "mae_log": metrics["mae_log"],
            "rmse_log": metrics["rmse_log"],
            "medape": metrics["medape"],
            "wape": metrics["wape"],

            "melhoria_vs_v0_pct":
                melhoria_vs_v0,
        }

        resultados.append(resultado)

        if metrics["mae_log"] < melhor_mae:
            melhor_mae = metrics["mae_log"]
            melhor_errors = errors.copy()
            melhor_nome = candidato["nome"]

        print(
            f"best_iteration: "
            f"{best_iteration}"
        )

        print(
            f"MAE log:        "
            f"{metrics['mae_log']:.6f}"
        )

        print(
            f"RMSE log:       "
            f"{metrics['rmse_log']:.6f}"
        )

        print(
            f"MedAPE:         "
            f"{metrics['medape']:.2f}%"
        )

        print(
            f"WAPE:           "
            f"{metrics['wape']:.2f}%"
        )

        print(
            f"Melhoria vs v0: "
            f"{melhoria_vs_v0:+.2f}%"
        )

    # ---------------------------------------------------------
    # 6. Ranking
    # ---------------------------------------------------------
    print("\n[6/6] Consolidando ranking...")

    ranking = (
        pd.DataFrame(resultados)
        .sort_values(
            "mae_log",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    print("\n" + "=" * 85)
    print("RANKING — LIGHTGBM TUNING STAGE 2")
    print("=" * 85)

    tabela = ranking[
        [
            "nome",
            "learning_rate",
            "reg_alpha",
            "reg_lambda",
            "best_iteration",
            "mae_log",
            "rmse_log",
            "medape",
            "wape",
            "melhoria_vs_v0_pct",
        ]
    ]

    print(
        tabela.to_string(
            index=False,
            formatters={
                "mae_log":
                    "{:.6f}".format,

                "rmse_log":
                    "{:.6f}".format,

                "medape":
                    "{:.2f}%".format,

                "wape":
                    "{:.2f}%".format,

                "melhoria_vs_v0_pct":
                    "{:+.2f}%".format,
            },
        )
    )

    melhor = ranking.iloc[0]

    print("\n" + "=" * 85)
    print("MELHOR CANDIDATO STAGE 2")
    print("=" * 85)

    print(
        f"Nome:              "
        f"{melhor['nome']}"
    )

    print(
        f"learning_rate:     "
        f"{melhor['learning_rate']}"
    )

    print(
        f"reg_alpha:         "
        f"{melhor['reg_alpha']}"
    )

    print(
        f"reg_lambda:        "
        f"{melhor['reg_lambda']}"
    )

    print(
        f"best_iteration:    "
        f"{int(melhor['best_iteration'])}"
    )

    print(
        f"MAE log:           "
        f"{melhor['mae_log']:.6f}"
    )

    print(
        f"Melhoria vs v0:    "
        f"{melhor['melhoria_vs_v0_pct']:+.2f}%"
    )

    # ---------------------------------------------------------
    # Persistencia
    # ---------------------------------------------------------
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        OUTPUT_DIR
        / "lightgbm_tuning_stage2_2025.csv"
    )

    json_path = (
        OUTPUT_DIR
        / "lightgbm_tuning_stage2_2025.json"
    )

    errors_path = (
        OUTPUT_DIR
        / "lightgbm_tuned_validation_2025_errors.parquet"
    )

    ranking.to_csv(
        csv_path,
        index=False,
    )

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            resultados,
            f,
            indent=2,
            ensure_ascii=False,
        )

    if melhor_errors is None:
        raise RuntimeError(
            "Nenhum candidato valido encontrado"
        )

    melhor_errors = melhor_errors.copy()

    melhor_errors["model"] = (
        "LightGBM_tuned_"
        + str(melhor_nome)
    )

    melhor_errors.to_parquet(
        errors_path,
        index=False,
    )

    print("\nARQUIVOS SALVOS")
    print(csv_path)
    print(json_path)
    print(errors_path)

    print("\n" + "=" * 85)
    print("2026 permanece intocado.")
    print("=" * 85)


if __name__ == "__main__":
    main()