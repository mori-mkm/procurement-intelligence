"""
Fase 13.14.3 - Savings Opportunities calibradas | OOT 2026.

Fluxo:
2025 -> threshold de anomalia calibrado
2026 -> anomalias com threshold congelado
     -> somente known
     -> somente acima do esperado
     -> potential savings
     -> priorizacao por impacto financeiro

IMPORTANTE:
Potential Savings Opportunity nao significa fraude,
sobrepreco comprovado ou economia garantida.
E apenas um ranking para revisao de Procurement.
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
from src.analytics.price_ml import engineer_features
from src.analytics.savings_engine import (
    compute_savings_opportunity,
    rank_savings_by_category,
    summarize_savings,
    classify_savings_priority,
)


def main():
    print("=" * 90)
    print("FASE 13.14.3 - CALIBRATED SAVINGS OPPORTUNITIES | 2026")
    print("=" * 90)

    # ---------------------------------------------------------
    # 1. Carregar anomalias calibradas
    # ---------------------------------------------------------
    print("\n[1/7] Carregando anomalias calibradas...")

    anomaly_path = (
        OUTPUT_DIR
        / "anomalies_oot_2026.parquet"
    )

    if not anomaly_path.exists():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {anomaly_path}"
        )

    anomalies = pd.read_parquet(
        anomaly_path
    )

    print(
        f"Registros OOT 2026:             "
        f"{len(anomalies):,}"
    )

    print(
        f"Anomalias totais:               "
        f"{int(anomalies['is_price_anomaly'].sum()):,}"
    )

    acima = (
        anomalies["anomaly_direction"]
        == "acima_do_esperado"
    )

    print(
        f"Anomalias acima do esperado:    "
        f"{int(acima.sum()):,}"
    )

    # ---------------------------------------------------------
    # 2. Recarregar populacao oficial para metadados
    # ---------------------------------------------------------
    print("\n[2/7] Reanexando metadados de Procurement...")

    gold = load_gold_layer()

    fact = gold["fact_purchase"]
    dim_supplier = gold["dim_supplier"]

    df = prepare_baseline_dataset(
        fact
    )

    df = engineer_features(
        df
    )

    splits = split_temporal(
        df
    )

    teste_2026 = splits["teste"].copy()

    metadata_cols = [
        "purchase_item_id",
        "supplier_key",
        "buyer_key",
        "unidade_orgao_uf_sigla",
        "modalidade_nome",
        "date_key",
        "quantity",
        "total_price",
        "categoria_relevante",
    ]

    faltantes = (
        set(metadata_cols)
        - set(teste_2026.columns)
    )

    if faltantes:
        raise ValueError(
            "Colunas ausentes no teste 2026: "
            f"{sorted(faltantes)}"
        )

    metadata = (
        teste_2026[
            metadata_cols
        ]
        .copy()
    )

    metadata["observation_id"] = (
        metadata.index
    )

    enriched = anomalies.merge(
        metadata,
        on="observation_id",
        how="left",
        validate="one_to_one",
    )

    if len(enriched) != len(anomalies):
        raise ValueError(
            "Join de metadados alterou o numero de linhas"
        )

    if enriched["quantity"].isna().any():
        raise ValueError(
            "Existem registros sem quantity apos o join"
        )

    # ---------------------------------------------------------
    # 3. Nome do fornecedor
    # ---------------------------------------------------------
    print("\n[3/7] Reanexando fornecedores...")

    supplier_lookup = (
        dim_supplier[
            [
                "supplier_key",
                "nome_fornecedor",
            ]
        ]
        .drop_duplicates(
            subset="supplier_key"
        )
    )

    enriched = enriched.merge(
        supplier_lookup,
        on="supplier_key",
        how="left",
        validate="many_to_one",
    )

    enriched["data"] = pd.to_datetime(
        enriched["date_key"]
        .astype("Int64")
        .astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    print(
        "Integridade dos joins: OK"
    )

    # ---------------------------------------------------------
    # 4. Savings Opportunity
    # ---------------------------------------------------------
    print("\n[4/7] Calculando Potential Savings...")

    savings = compute_savings_opportunity(
        enriched
    )

    # A calibracao foi known-only.
    if (
        ~savings["is_known_item"]
        .fillna(False)
        .astype(bool)
    ).any():
        raise ValueError(
            "Oportunidade unseen encontrada. "
            "Esperado somente known."
        )

    savings = classify_savings_priority(
        savings
    )

    print(
        f"Oportunidades calculadas:       "
        f"{len(savings):,}"
    )

    # ---------------------------------------------------------
    # 5. Resumo financeiro
    # ---------------------------------------------------------
    print("\n[5/7] Consolidando impacto financeiro...")

    summary = summarize_savings(
        savings
    )

    prioridade = (
        savings
        .groupby(
            "priority",
            dropna=False,
        )
        .agg(
            n_oportunidades=(
                "potential_saving",
                "size",
            ),
            potential_saving=(
                "potential_saving",
                "sum",
            ),
        )
        .reset_index()
    )

    ordem_prioridade = {
        "Alta": 1,
        "Media": 2,
        "Baixa": 3,
    }

    prioridade["_ordem"] = (
        prioridade["priority"]
        .map(ordem_prioridade)
    )

    prioridade = (
        prioridade
        .sort_values("_ordem")
        .drop(columns="_ordem")
    )

    print("\n" + "=" * 90)
    print("RESUMO — POTENTIAL SAVINGS 2026")
    print("=" * 90)

    print(
        f"N oportunidades:              "
        f"{summary['n_oportunidades_total']:,}"
    )

    print(
        f"Potential Savings total:      "
        f"R$ "
        f"{summary['savings_potencial_total']:,.2f}"
    )

    print(
        f"Excluindo ticket alto:        "
        f"R$ "
        f"{summary['savings_potencial_excluindo_ticket_alto']:,.2f}"
    )

    print(
        f"Oportunidades ticket alto:    "
        f"{summary['n_oportunidades_ticket_alto_cautela']:,}"
    )

    print("\nPRIORIDADE")

    print(
        prioridade.to_string(
            index=False,
            formatters={
                "potential_saving":
                    "R$ {:,.2f}".format,
            },
        )
    )

    # ---------------------------------------------------------
    # 6. Rankings
    # ---------------------------------------------------------
    print("\n[6/7] Criando rankings...")

    categoria = rank_savings_by_category(
        savings
    )

    fornecedor = (
        savings
        .groupby(
            [
                "supplier_key",
                "nome_fornecedor",
            ],
            dropna=False,
        )
        .agg(
            savings_potencial_total=(
                "potential_saving",
                "sum",
            ),
            n_oportunidades=(
                "potential_saving",
                "size",
            ),
            n_ticket_alto_cautela=(
                "ticket_alto_cautela",
                "sum",
            ),
        )
        .reset_index()
        .sort_values(
            "savings_potencial_total",
            ascending=False,
        )
    )

    print("\n" + "=" * 90)
    print("TOP 15 OPORTUNIDADES")
    print("=" * 90)

    colunas_top = [
        "priority",
        "purchase_item_id",
        "nome_fornecedor",
        "categoria_relevante",
        "unit_price",
        "preco_esperado",
        "quantity",
        "price_deviation_pct",
        "potential_saving",
        "ticket_alto_cautela",
    ]

    print(
        savings[
            colunas_top
        ]
        .head(15)
        .to_string(
            index=False,
            formatters={
                "unit_price":
                    "R$ {:,.2f}".format,

                "preco_esperado":
                    "R$ {:,.2f}".format,

                "price_deviation_pct":
                    "{:+,.2f}%".format,

                "potential_saving":
                    "R$ {:,.2f}".format,
            },
        )
    )

    print("\n" + "=" * 90)
    print("TOP CATEGORIAS")
    print("=" * 90)

    print(
        categoria.head(10).to_string(
            index=False,
            formatters={
                "savings_potencial_total":
                    "R$ {:,.2f}".format,
            },
        )
    )

    # ---------------------------------------------------------
    # 7. Persistir
    # ---------------------------------------------------------
    print("\n[7/7] Salvando resultados...")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    savings_parquet_path = (
        OUTPUT_DIR
        / "savings_opportunities_oot_2026.parquet"
    )

    savings_csv_path = (
        OUTPUT_DIR
        / "savings_opportunities_oot_2026.csv"
    )

    categoria_path = (
        OUTPUT_DIR
        / "savings_by_category_oot_2026.csv"
    )

    fornecedor_path = (
        OUTPUT_DIR
        / "savings_by_supplier_oot_2026.csv"
    )

    prioridade_path = (
        OUTPUT_DIR
        / "savings_by_priority_oot_2026.csv"
    )

    summary_path = (
        OUTPUT_DIR
        / "savings_oot_2026_summary.json"
    )

    savings.to_parquet(
        savings_parquet_path,
        index=False,
    )

    savings.to_csv(
        savings_csv_path,
        index=False,
    )

    categoria.to_csv(
        categoria_path,
        index=False,
    )

    fornecedor.to_csv(
        fornecedor_path,
        index=False,
    )

    prioridade.to_csv(
        prioridade_path,
        index=False,
    )

    payload = {
        "interpretation": (
            "Potential Savings Opportunity e um indicador "
            "para priorizacao de revisao e negociacao. "
            "Nao representa fraude, sobrepreco comprovado "
            "ou economia garantida."
        ),

        "methodology": {
            "anomaly_threshold_calibration":
                "2025 validation",
            "test_period":
                "2026 OOT",
            "known_only":
                True,
            "direction":
                "acima_do_esperado",
            "formula":
                "max(unit_price - expected_price, 0) * quantity",
        },

        "summary": summary,

        "priority": prioridade.to_dict(
            orient="records"
        ),
    }

    with summary_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            payload,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\nARQUIVOS SALVOS")
    print(savings_parquet_path)
    print(savings_csv_path)
    print(categoria_path)
    print(fornecedor_path)
    print(prioridade_path)
    print(summary_path)

    print("\n" + "=" * 90)
    print("FIM — CALIBRATED SAVINGS OPPORTUNITIES")
    print("=" * 90)


if __name__ == "__main__":
    main()