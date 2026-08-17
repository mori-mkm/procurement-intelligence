"""
Fase 13.3 - Avaliacao do LightGBM v0 na validacao temporal de 2025.

Objetivo:
- preservar o LightGBM atual sem tuning;
- treinar exclusivamente em 2024;
- avaliar exclusivamente em 2025;
- nao usar metricas de 2026 durante selecao de modelos.
"""

import sys
import json
from pathlib import Path


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


def main():
    print("=" * 70)
    print("FASE 13.3 - LIGHTGBM V0 | VALIDACAO 2025")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Carregar Gold
    # ---------------------------------------------------------
    print("\n[1/6] Carregando Gold...")

    gold = load_gold_layer()
    fact = gold["fact_purchase"]

    print(f"Fact purchase: {len(fact):,} linhas")

    # ---------------------------------------------------------
    # 2. Aplicar exatamente o mesmo escopo da modelagem atual
    # ---------------------------------------------------------
    print("\n[2/6] Preparando dataset...")

    df = prepare_baseline_dataset(fact)
    df = engineer_features(df)

    print(f"Dataset apos filtros: {len(df):,} linhas")

    # ---------------------------------------------------------
    # 3. Split temporal
    # ---------------------------------------------------------
    print("\n[3/6] Aplicando split temporal...")

    splits = split_temporal(df)

    # Mantemos uma versao original dos dados para preservar
    # observation_id, item_key e demais metadados da transacao.
    #
    # A versao transformada sera usada SOMENTE como entrada
    # do LightGBM.
    treino_raw = splits["treino"].copy()
    validacao_raw = splits["validacao"].copy()

    print(f"Treino 2024:     {len(treino_raw):,}")
    print(f"Validacao 2025: {len(validacao_raw):,}")

    print("\nIMPORTANTE: 2026 nao sera avaliado nesta etapa.")

    # ---------------------------------------------------------
    # Identidade dos itens antes de qualquer transformacao
    # ---------------------------------------------------------
    train_item_keys = (
        treino_raw["item_key"]
        .dropna()
        .unique()
    )

    # ---------------------------------------------------------
    # 4. Alinhar categorias usando SOMENTE o treino
    #
    # Estas copias sao exclusivas para entrada do modelo.
    # O validacao_raw permanece intacto para auditoria.
    # ---------------------------------------------------------
    print("\n[4/6] Alinhando categorias...")

    treino_modelo, validacao_modelo = align_categorical_dtypes(
        treino_raw.copy(),
        validacao_raw.copy(),
    )

    # ---------------------------------------------------------
    # 5. Treinar LightGBM original
    # ---------------------------------------------------------
    print("\n[5/6] Treinando LightGBM v0...")

    modelo = train_lightgbm_model(
        treino_modelo
    )

    features = (
        FEATURES_CATEGORICAS
        + FEATURES_NUMERICAS
    )

    log_pred = modelo.predict(
        validacao_modelo[features]
    )

    # ---------------------------------------------------------
    # 6. Avaliar com a regua unica
    # ---------------------------------------------------------
    print("\n[6/6] Calculando metricas...")

    # IMPORTANTE:
    # previsao vem do DataFrame preparado para o modelo,
    # mas metadados vêm do DataFrame original.
    errors = build_prediction_errors(
        df=validacao_raw,
        log_pred=log_pred,
        model_name="LightGBM_v0",
        train_item_keys=train_item_keys,
    )

    metrics = evaluate_prediction_errors(errors)

    print("\n" + "=" * 70)
    print("RESULTADO — LIGHTGBM V0 | VALIDACAO 2025")
    print("=" * 70)

    print(f"N transacoes:       {metrics['n_transacoes']:,}")
    print(f"MAE log:            {metrics['mae_log']:.6f}")
    print(f"RMSE log:           {metrics['rmse_log']:.6f}")
    print(f"MedAPE:             {metrics['medape']:.2f}%")
    print(f"WAPE:               {metrics['wape']:.2f}%")
    print(f"MAE preco:          R$ {metrics['mae']:,.2f}")
    print(f"RMSE preco:         R$ {metrics['rmse']:,.2f}")
    print(f"Known item rate:    {metrics['known_item_rate']:.2f}%")
    print(f"Unseen item rate:   {metrics['unseen_item_rate']:.2f}%")

    # ---------------------------------------------------------
    # Diagnostico adicional: erro known vs unseen
    # ---------------------------------------------------------
    known = errors[errors["is_known_item"]]
    unseen = errors[~errors["is_known_item"]]

    print("\n" + "-" * 70)
    print("DESEMPENHO POR COLD START")
    print("-" * 70)

    if not known.empty:
        known_metrics = evaluate_prediction_errors(known)

        print("\nKNOWN ITEMS")
        print(f"N:                  {len(known):,}")
        print(f"MAE log:            {known_metrics['mae_log']:.6f}")
        print(f"MedAPE:             {known_metrics['medape']:.2f}%")
        print(f"WAPE:               {known_metrics['wape']:.2f}%")

    if not unseen.empty:
        unseen_metrics = evaluate_prediction_errors(unseen)

        print("\nUNSEEN ITEMS")
        print(f"N:                  {len(unseen):,}")
        print(f"MAE log:            {unseen_metrics['mae_log']:.6f}")
        print(f"MedAPE:             {unseen_metrics['medape']:.2f}%")
        print(f"WAPE:               {unseen_metrics['wape']:.2f}%")

    # ---------------------------------------------------------
    # Persistir resultados para comparacao futura
    # ---------------------------------------------------------
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    errors_path = (
        OUTPUT_DIR
        / "lightgbm_v0_validation_2025_errors.parquet"
    )

    metrics_path = (
        OUTPUT_DIR
        / "lightgbm_v0_validation_2025_metrics.json"
    )

    errors.to_parquet(
        errors_path,
        index=False,
    )

    with metrics_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metrics,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "-" * 70)
    print("ARQUIVOS SALVOS")
    print("-" * 70)
    print(errors_path)
    print(metrics_path)

    print("\n" + "=" * 70)
    print("FIM — nenhum resultado de 2026 foi utilizado.")
    print("=" * 70)


if __name__ == "__main__":
    main()