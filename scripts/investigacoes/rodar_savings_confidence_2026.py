"""
Fase 13.14.5 - Dataset oficial de Savings para o dashboard.

Objetivo:
- ler a auditoria das oportunidades OOT 2026;
- classificar confiabilidade;
- separar KPI executivo de itens que exigem revisao;
- gerar dataset final para consumo pelo dashboard.

Confidence tiers:
Alta
Revisao Alto Valor
Baixa
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


from src.analytics.savings_engine import (
    classify_savings_confidence,
)


BOOLEAN_COLS = [
    "ticket_alto_cautela",
    "flag_pouco_historico",
    "flag_unidade_nao_comparavel",
    "flag_inconsistencia_total",
    "flag_resultado_conflitante",
]


def normalizar_booleano(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    return (
        series
        .astype("string")
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
        .fillna(False)
        .astype(bool)
    )


def main():
    print("=" * 90)
    print("FASE 13.14.5 - SAVINGS CONFIDENCE TIERS | 2026")
    print("=" * 90)

    # ---------------------------------------------------------
    # 1. Auditoria
    # ---------------------------------------------------------
    print("\n[1/5] Carregando auditoria...")

    input_path = (
        OUTPUT_DIR
        / "savings_audit_oot_2026.csv"
    )

    if not input_path.exists():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {input_path}"
        )

    savings = pd.read_csv(
    input_path,
    dtype={
        "purchase_item_id": "string",
        "supplier_key": "string",
        "item_key": "string",
    },
    low_memory=False,
    )

    print(
        f"Oportunidades auditadas: {len(savings):,}"
    )

    # ---------------------------------------------------------
    # 2. Normalizar flags
    # ---------------------------------------------------------
    print("\n[2/5] Normalizando flags...")

    for coluna in BOOLEAN_COLS:

        if coluna not in savings.columns:
            raise ValueError(
                f"Coluna obrigatoria ausente: {coluna}"
            )

        savings[coluna] = normalizar_booleano(
            savings[coluna]
        )

    # ---------------------------------------------------------
    # 3. Confidence tier
    # ---------------------------------------------------------
    print("\n[3/5] Classificando confiabilidade...")

    savings = classify_savings_confidence(
        savings
    )

    # ---------------------------------------------------------
    # 4. Consolidacao
    # ---------------------------------------------------------
    print("\n[4/5] Consolidando resultados...")

    resumo = (
        savings
        .groupby(
            "confidence_tier",
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

    ordem = {
        "Alta": 1,
        "Revisao Alto Valor": 2,
        "Baixa": 3,
    }

    resumo["_ordem"] = (
        resumo["confidence_tier"]
        .map(ordem)
    )

    resumo = (
        resumo
        .sort_values("_ordem")
        .drop(columns="_ordem")
        .reset_index(drop=True)
    )

    total = float(
        savings["potential_saving"].sum()
    )

    resumo["share_savings_pct"] = (
        100
        * resumo["potential_saving"]
        / total
    )

    alta = savings[
        savings["confidence_tier"]
        == "Alta"
    ].copy()

    revisao = savings[
        savings["confidence_tier"]
        == "Revisao Alto Valor"
    ].copy()

    baixa = savings[
        savings["confidence_tier"]
        == "Baixa"
    ].copy()

    kpi_high_confidence = float(
        alta["potential_saving"].sum()
    )

    kpi_review = float(
        revisao["potential_saving"].sum()
    )

    print("\n" + "=" * 90)
    print("CONFIDENCE TIERS")
    print("=" * 90)

    print(
        resumo.to_string(
            index=False,
            formatters={
                "potential_saving":
                    "R$ {:,.2f}".format,

                "share_savings_pct":
                    "{:.2f}%".format,
            },
        )
    )

    print("\n" + "=" * 90)
    print("KPIs RECOMENDADOS PARA O DASHBOARD")
    print("=" * 90)

    print(
        f"Potential Savings — High Confidence: "
        f"R$ {kpi_high_confidence:,.2f}"
    )

    print(
        f"N oportunidades High Confidence:     "
        f"{len(alta):,}"
    )

    print(
        f"High-Value Opportunities Under Review:"
        f" R$ {kpi_review:,.2f}"
    )

    print(
        f"N oportunidades em revisao:          "
        f"{len(revisao):,}"
    )

    print(
        f"Oportunidades baixa confianca:        "
        f"{len(baixa):,}"
    )

    # ---------------------------------------------------------
    # 5. Dataset oficial do dashboard
    # ---------------------------------------------------------
    print("\n[5/5] Salvando dataset oficial...")

    colunas_dashboard = [
        "observation_id",
        "purchase_item_id",
        "item_key",
        "descricao_resumida_amostra",
        "categoria_relevante",
        "supplier_key",
        "nome_fornecedor",
        "unit_price",
        "preco_esperado",
        "quantity",
        "total_price",
        "price_deviation_pct",
        "potential_saving",
        "priority",
        "confidence_tier",
        "n_historico",
        "preco_hist_mediana",
        "price_vs_hist_median_x",
        "unit_flag",
        "ticket_alto_cautela",
        "flag_pouco_historico",
        "flag_unidade_nao_comparavel",
        "flag_inconsistencia_total",
        "flag_resultado_conflitante",
        "n_flags_cautela",
    ]

    faltantes = (
        set(colunas_dashboard)
        - set(savings.columns)
    )

    if faltantes:
        raise ValueError(
            "Colunas ausentes para dashboard: "
            f"{sorted(faltantes)}"
        )

    dashboard = (
        savings[
            colunas_dashboard
        ]
        .sort_values(
            [
                "confidence_tier",
                "potential_saving",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .copy()
    )

    dashboard_parquet = (
        OUTPUT_DIR
        / "savings_dashboard_oot_2026.parquet"
    )

    dashboard_csv = (
        OUTPUT_DIR
        / "savings_dashboard_oot_2026.csv"
    )

    resumo_path = (
        OUTPUT_DIR
        / "savings_confidence_oot_2026.csv"
    )

    summary_json = (
        OUTPUT_DIR
        / "savings_dashboard_oot_2026_summary.json"
    )

    dashboard.to_parquet(
        dashboard_parquet,
        index=False,
    )

    dashboard.to_csv(
        dashboard_csv,
        index=False,
    )

    resumo.to_csv(
        resumo_path,
        index=False,
    )

    payload = {
        "dashboard_kpis": {
            "potential_savings_high_confidence":
                kpi_high_confidence,

            "n_high_confidence":
                int(len(alta)),

            "potential_savings_high_value_review":
                kpi_review,

            "n_high_value_review":
                int(len(revisao)),

            "n_low_confidence":
                int(len(baixa)),
        },

        "definitions": {
            "Alta": (
                "Unidade comparavel, historico suficiente, "
                "sem inconsistencias, sem conflito e sem "
                "flag de ticket alto."
            ),

            "Revisao Alto Valor": (
                "Qualidade adequada, mas ticket alto exige "
                "validacao manual."
            ),

            "Baixa": (
                "Possui problema de comparabilidade, pouco "
                "historico, inconsistencias ou conflito."
            ),
        },

        "warning": (
            "Potential Savings e indicador de priorizacao. "
            "Nao representa economia garantida, fraude ou "
            "sobrepreco comprovado."
        ),
    }

    with summary_json.open(
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
    print(dashboard_parquet)
    print(dashboard_csv)
    print(resumo_path)
    print(summary_json)

    print("\n" + "=" * 90)
    print("FIM — DATASET OFICIAL DE SAVINGS PARA O DASHBOARD")
    print("=" * 90)


if __name__ == "__main__":
    main()