"""
Fase 13.13.1 - Final Out-of-Time Evaluation 2026.

PROTOCOLO CONGELADO:

2024
    desenvolvimento / treino inicial

2025
    model selection + tuning

2024 + 2025
    treino final

2026
    teste final out-of-time

Modelo congelado:
    LightGBM v0

Nenhuma decisao de algoritmo ou hiperparametro pode ser alterada
com base nos resultados de 2026.
"""

import json
import sys
from pathlib import Path

import pandas as pd


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
    train_lightgbm_model,
)
from src.analytics.model_selection import (
    build_prediction_errors,
    evaluate_prediction_errors,
)


FEATURES = (
    FEATURES_CATEGORICAS
    + FEATURES_NUMERICAS
)


def main():
    print("=" * 85)
    print("FASE 13.13.1 - FINAL OUT-OF-TIME TEST | 2026")
    print("=" * 85)

    # ---------------------------------------------------------
    # 1. Carregar Gold
    # ---------------------------------------------------------
    print("\n[1/7] Carregando Gold...")

    gold = load_gold_layer()
    fact = gold["fact_purchase"]

    print(
        f"Fact purchase: {len(fact):,} linhas"
    )

    # ---------------------------------------------------------
    # 2. Populacao oficial de Price Intelligence
    # ---------------------------------------------------------
    print("\n[2/7] Preparando dataset...")

    df = prepare_baseline_dataset(fact)
    df = engineer_features(df)

    print(
        f"Dataset apos filtros: {len(df):,} linhas"
    )

    # ---------------------------------------------------------
    # 3. Split temporal ja definido
    # ---------------------------------------------------------
    print("\n[3/7] Aplicando split temporal congelado...")

    splits = split_temporal(df)

    treino_2024 = splits["treino"].copy()
    validacao_2025 = splits["validacao"].copy()
    teste_2026 = splits["teste"].copy()

    print(
        f"Treino original 2024:     "
        f"{len(treino_2024):,}"
    )

    print(
        f"Validacao original 2025:  "
        f"{len(validacao_2025):,}"
    )

    print(
        f"Teste OOT 2026:           "
        f"{len(teste_2026):,}"
    )

    if len(teste_2026) == 0:
        raise ValueError(
            "O conjunto de teste 2026 esta vazio"
        )

    # ---------------------------------------------------------
    # 4. Historico final = 2024 + 2025
    # ---------------------------------------------------------
    print("\n[4/7] Construindo treino final 2024 + 2025...")

    historico_raw = pd.concat(
        [
            treino_2024,
            validacao_2025,
        ],
        axis=0,
    ).copy()

    if historico_raw.index.duplicated().any():
        raise ValueError(
            "Indices duplicados no historico 2024+2025"
        )

    if teste_2026.index.duplicated().any():
        raise ValueError(
            "Indices duplicados no teste 2026"
        )

    intersecao = (
        set(historico_raw.index)
        & set(teste_2026.index)
    )

    if intersecao:
        raise ValueError(
            "Leakage detectado: existem observation_id "
            "presentes no historico e no teste"
        )

    print(
        f"Historico 2024+2025:      "
        f"{len(historico_raw):,}"
    )

    print(
        f"Teste 2026:               "
        f"{len(teste_2026):,}"
    )

    print(
        "Sobreposicao treino/teste: 0"
    )

    # ---------------------------------------------------------
    # 5. Preparar categorias
    #
    # IMPORTANTE:
    # categorias sao aprendidas apenas em 2024+2025.
    # categorias novas de 2026 tornam-se missing para o modelo.
    #
    # teste_2026 original permanece intacto para auditoria.
    # ---------------------------------------------------------
    print("\n[5/7] Preparando features...")

    historico_modelo, teste_modelo = (
        align_categorical_dtypes(
            historico_raw.copy(),
            teste_2026.copy(),
        )
    )

    train_item_keys = (
        historico_raw["item_key"]
        .dropna()
        .unique()
    )

    print(
        f"Item keys conhecidos no historico: "
        f"{len(train_item_keys):,}"
    )

    # ---------------------------------------------------------
    # 6. Treinar modelo FINAL
    #
    # train_lightgbm_model representa o LightGBM v0
    # congelado antes da abertura de 2026.
    # ---------------------------------------------------------
    print("\n[6/7] Treinando LightGBM final...")

    modelo = train_lightgbm_model(
        historico_modelo
    )

    log_pred = modelo.predict(
        teste_modelo[FEATURES]
    )

    # ---------------------------------------------------------
    # 7. Avaliar 2026
    # ---------------------------------------------------------
    print("\n[7/7] Avaliando teste OOT 2026...")

    errors = build_prediction_errors(
        df=teste_2026,
        log_pred=log_pred,
        model_name="LightGBM_final_2026",
        train_item_keys=train_item_keys,
    )

    metrics = evaluate_prediction_errors(
        errors
    )

    known = errors[
        errors["is_known_item"]
    ].copy()

    unseen = errors[
        ~errors["is_known_item"]
    ].copy()

    known_metrics = (
        evaluate_prediction_errors(known)
        if len(known) > 0
        else None
    )

    unseen_metrics = (
        evaluate_prediction_errors(unseen)
        if len(unseen) > 0
        else None
    )

    # ---------------------------------------------------------
    # Resultado principal
    # ---------------------------------------------------------
    print("\n" + "=" * 85)
    print("RESULTADO FINAL — OOT 2026")
    print("=" * 85)

    print(
        f"N transacoes:       "
        f"{metrics['n_transacoes']:,}"
    )

    print(
        f"MAE log:            "
        f"{metrics['mae_log']:.6f}"
    )

    print(
        f"RMSE log:           "
        f"{metrics['rmse_log']:.6f}"
    )

    print(
        f"MedAPE:             "
        f"{metrics['medape']:.2f}%"
    )

    print(
        f"WAPE:               "
        f"{metrics['wape']:.2f}%"
    )

    print(
        f"MAE preco:          "
        f"R$ {metrics['mae']:,.2f}"
    )

    print(
        f"RMSE preco:         "
        f"R$ {metrics['rmse']:,.2f}"
    )

    print(
        f"Known item rate:    "
        f"{metrics['known_item_rate']:.2f}%"
    )

    print(
        f"Unseen item rate:   "
        f"{metrics['unseen_item_rate']:.2f}%"
    )

    # ---------------------------------------------------------
    # Cold start
    # ---------------------------------------------------------
    print("\n" + "-" * 85)
    print("DESEMPENHO POR COLD START")
    print("-" * 85)

    if known_metrics is not None:

        print("\nKNOWN ITEMS")

        print(
            f"N:                  "
            f"{known_metrics['n_transacoes']:,}"
        )

        print(
            f"MAE log:            "
            f"{known_metrics['mae_log']:.6f}"
        )

        print(
            f"RMSE log:           "
            f"{known_metrics['rmse_log']:.6f}"
        )

        print(
            f"MedAPE:             "
            f"{known_metrics['medape']:.2f}%"
        )

        print(
            f"WAPE:               "
            f"{known_metrics['wape']:.2f}%"
        )

    if unseen_metrics is not None:

        print("\nUNSEEN ITEMS")

        print(
            f"N:                  "
            f"{unseen_metrics['n_transacoes']:,}"
        )

        print(
            f"MAE log:            "
            f"{unseen_metrics['mae_log']:.6f}"
        )

        print(
            f"RMSE log:           "
            f"{unseen_metrics['rmse_log']:.6f}"
        )

        print(
            f"MedAPE:             "
            f"{unseen_metrics['medape']:.2f}%"
        )

        print(
            f"WAPE:               "
            f"{unseen_metrics['wape']:.2f}%"
        )

    # ---------------------------------------------------------
    # Persistir
    # ---------------------------------------------------------
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    errors_path = (
        OUTPUT_DIR
        / "lightgbm_final_oot_2026_errors.parquet"
    )

    metrics_path = (
        OUTPUT_DIR
        / "lightgbm_final_oot_2026_metrics.json"
    )

    errors.to_parquet(
        errors_path,
        index=False,
    )

    resultado_json = {
        "protocol": {
            "development_train": 2024,
            "validation_model_selection": 2025,
            "final_train": "2024+2025",
            "final_test": 2026,
            "model": "LightGBM_v0",
            "retuning_after_test_allowed": False,
        },
        "sample_sizes": {
            "train_2024": int(
                len(treino_2024)
            ),
            "validation_2025": int(
                len(validacao_2025)
            ),
            "final_train_2024_2025": int(
                len(historico_raw)
            ),
            "test_2026": int(
                len(teste_2026)
            ),
        },
        "overall": metrics,
        "known_items": known_metrics,
        "unseen_items": unseen_metrics,
    }

    with metrics_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            resultado_json,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "-" * 85)
    print("ARQUIVOS SALVOS")
    print("-" * 85)

    print(errors_path)
    print(metrics_path)

    print("\n" + "=" * 85)
    print("TESTE OOT 2026 CONCLUIDO.")
    print("Nenhum retuning sera realizado com base neste resultado.")
    print("=" * 85)


if __name__ == "__main__":
    main()