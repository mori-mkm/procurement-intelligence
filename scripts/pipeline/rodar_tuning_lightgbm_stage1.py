"""
Fase 13.12.1 - LightGBM tuning: complexidade das arvores.

Objetivo:
- treino exclusivamente em 2024;
- tuning exclusivamente em 2025;
- 2026 permanece intocado;
- criterio primario: menor MAE no log do preco;
- variar apenas num_leaves e min_child_samples;
- usar early stopping para determinar numero de arvores.
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
# Grid pequeno e definido ANTES de olhar os resultados.
# -------------------------------------------------------------
CANDIDATOS = [
    {
        "nome": "L31_M10",
        "num_leaves": 31,
        "min_child_samples": 10,
    },
    {
        "nome": "L31_M20",
        "num_leaves": 31,
        "min_child_samples": 20,
    },
    {
        "nome": "L31_M50",
        "num_leaves": 31,
        "min_child_samples": 50,
    },
    {
        "nome": "L63_M10",
        "num_leaves": 63,
        "min_child_samples": 10,
    },
    {
        "nome": "L63_M20",
        "num_leaves": 63,
        "min_child_samples": 20,
    },
    {
        "nome": "L63_M50",
        "num_leaves": 63,
        "min_child_samples": 50,
    },
    {
        "nome": "L127_M20",
        "num_leaves": 127,
        "min_child_samples": 20,
    },
    {
        "nome": "L127_M50",
        "num_leaves": 127,
        "min_child_samples": 50,
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

    return float(
        metrics["mae_log"]
    )


def main():
    print("=" * 85)
    print("FASE 13.12.1 - LIGHTGBM TUNING | COMPLEXIDADE")
    print("=" * 85)

    # ---------------------------------------------------------
    # 1. Carregar Gold
    # ---------------------------------------------------------
    print("\n[1/6] Carregando Gold...")

    gold = load_gold_layer()
    fact = gold["fact_purchase"]

    print(
        f"Fact purchase: {len(fact):,} linhas"
    )

    # ---------------------------------------------------------
    # 2. Populacao oficial
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
    # 4. Preparar dados para LightGBM
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
            f"num_leaves={candidato['num_leaves']} | "
            f"min_child_samples="
            f"{candidato['min_child_samples']}"
        )

        modelo = LGBMRegressor(
            objective="regression",
            metric="l1",

            n_estimators=1200,
            learning_rate=0.05,

            num_leaves=candidato[
                "num_leaves"
            ],

            min_child_samples=candidato[
                "min_child_samples"
            ],

            reg_alpha=0.0,
            reg_lambda=0.0,

            random_state=42,
            n_jobs=-1,
            verbosity=-1,
        )

        modelo.fit(
            X_train,
            y_train,

            eval_set=[
                (
                    X_valid,
                    y_valid,
                )
            ],

            callbacks=[
                early_stopping(
                    stopping_rounds=50,
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
            "num_leaves": candidato[
                "num_leaves"
            ],
            "min_child_samples": candidato[
                "min_child_samples"
            ],
            "learning_rate": 0.05,
            "reg_alpha": 0.0,
            "reg_lambda": 0.0,
            "best_iteration": best_iteration,
            "mae_log": metrics["mae_log"],
            "rmse_log": metrics["rmse_log"],
            "medape": metrics["medape"],
            "wape": metrics["wape"],
            "melhoria_vs_v0_pct":
                melhoria_vs_v0,
        }

        resultados.append(resultado)

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
    print("RANKING — LIGHTGBM TUNING STAGE 1")
    print("=" * 85)

    tabela = ranking[
        [
            "nome",
            "num_leaves",
            "min_child_samples",
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
    print("MELHOR CANDIDATO")
    print("=" * 85)

    print(
        f"Nome:              "
        f"{melhor['nome']}"
    )

    print(
        f"num_leaves:        "
        f"{int(melhor['num_leaves'])}"
    )

    print(
        f"min_child_samples: "
        f"{int(melhor['min_child_samples'])}"
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
    # Persistir
    # ---------------------------------------------------------
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        OUTPUT_DIR
        / "lightgbm_tuning_stage1_2025.csv"
    )

    json_path = (
        OUTPUT_DIR
        / "lightgbm_tuning_stage1_2025.json"
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

    print("\nARQUIVOS SALVOS")
    print(csv_path)
    print(json_path)

    print("\n" + "=" * 85)
    print("2026 permanece intocado.")
    print("=" * 85)


if __name__ == "__main__":
    main()