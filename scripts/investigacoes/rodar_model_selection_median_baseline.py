"""
Fase 13.9 - Median Baseline na validacao temporal de 2025.

Objetivo:
- usar somente 2024 para construir o baseline;
- avaliar somente 2025;
- medir cobertura;
- avaliar com a mesma regua dos modelos supervisionados;
- preservar observation_id para comparacao same-sample futura;
- nao utilizar 2026.
"""

import json
import sys
from pathlib import Path

import numpy as np


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
    compute_median_baseline,
)
from src.analytics.model_selection import (
    build_prediction_errors,
    evaluate_prediction_errors,
)


def main():
    print("=" * 70)
    print("FASE 13.9 - MEDIAN BASELINE | VALIDACAO 2025")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Carregar Gold
    # ---------------------------------------------------------
    print("\n[1/6] Carregando Gold...")

    gold = load_gold_layer()
    fact = gold["fact_purchase"]

    print(f"Fact purchase: {len(fact):,} linhas")

    # ---------------------------------------------------------
    # 2. Populacao oficial limpa
    # ---------------------------------------------------------
    print("\n[2/6] Preparando dataset...")

    df = prepare_baseline_dataset(fact)

    print(f"Dataset apos filtros: {len(df):,} linhas")

    # ---------------------------------------------------------
    # 3. Split temporal
    # ---------------------------------------------------------
    print("\n[3/6] Aplicando split temporal...")

    splits = split_temporal(df)

    treino = splits["treino"]
    validacao = splits["validacao"]

    print(f"Treino 2024:     {len(treino):,}")
    print(f"Validacao 2025: {len(validacao):,}")

    print("\nIMPORTANTE: 2026 nao sera avaliado nesta etapa.")

    # ---------------------------------------------------------
    # 4. Construir baseline SOMENTE com 2024
    # ---------------------------------------------------------
    print("\n[4/6] Construindo median baseline...")

    baseline = compute_median_baseline(treino)

    baseline_confiavel = baseline[
        baseline["baseline_confiavel"]
    ].copy()

    print(
        f"Itens no treino:              {len(baseline):,}"
    )
    print(
        f"Itens com baseline confiavel: "
        f"{len(baseline_confiavel):,}"
    )

    # ---------------------------------------------------------
    # 5. Aplicar baseline em 2025
    # ---------------------------------------------------------
    print("\n[5/6] Aplicando baseline em 2025...")

    baseline_map = (
        baseline_confiavel
        .set_index("item_key")["preco_esperado"]
    )

    validacao_com_baseline = validacao.copy()

    validacao_com_baseline["preco_esperado"] = (
        validacao_com_baseline["item_key"]
        .map(baseline_map)
    )

    avaliavel = validacao_com_baseline[
        validacao_com_baseline["preco_esperado"].notna()
    ].copy()

    n_total = len(validacao_com_baseline)
    n_avaliavel = len(avaliavel)

    cobertura = (
        100 * n_avaliavel / n_total
        if n_total > 0
        else 0.0
    )

    print(f"Transacoes totais 2025:      {n_total:,}")
    print(f"Transacoes com baseline:     {n_avaliavel:,}")
    print(f"Cobertura:                   {cobertura:.2f}%")

    # ---------------------------------------------------------
    # 6. Avaliar com a mesma regua dos modelos
    # ---------------------------------------------------------
    print("\n[6/6] Calculando metricas...")

    log_pred = np.log(
        avaliavel["preco_esperado"].values
    )

    train_item_keys = (
        treino["item_key"]
        .dropna()
        .unique()
    )

    errors = build_prediction_errors(
        df=avaliavel,
        log_pred=log_pred,
        model_name="Median_Baseline",
        train_item_keys=train_item_keys,
    )

    metrics = evaluate_prediction_errors(errors)

    # Acrescenta metadados especificos do baseline
    metrics["n_transacoes_total_validacao"] = int(n_total)
    metrics["n_transacoes_com_baseline"] = int(n_avaliavel)
    metrics["pct_cobertura"] = float(cobertura)

    print("\n" + "=" * 70)
    print("RESULTADO — MEDIAN BASELINE | VALIDACAO 2025")
    print("=" * 70)

    print(f"N total validacao:   {n_total:,}")
    print(f"N com baseline:      {n_avaliavel:,}")
    print(f"Cobertura:           {cobertura:.2f}%")
    print(f"MAE log:             {metrics['mae_log']:.6f}")
    print(f"RMSE log:            {metrics['rmse_log']:.6f}")
    print(f"MedAPE:              {metrics['medape']:.2f}%")
    print(f"WAPE:                {metrics['wape']:.2f}%")
    print(f"MAE preco:           R$ {metrics['mae']:,.2f}")
    print(f"RMSE preco:          R$ {metrics['rmse']:,.2f}")

    # ---------------------------------------------------------
    # Persistir resultados
    # ---------------------------------------------------------
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    errors_path = (
        OUTPUT_DIR
        / "median_baseline_validation_2025_errors.parquet"
    )

    metrics_path = (
        OUTPUT_DIR
        / "median_baseline_validation_2025_metrics.json"
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