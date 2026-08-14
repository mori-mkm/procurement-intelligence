"""
Fase 13.14.4 - Auditoria das Savings Opportunities 2026.

Objetivo:
- verificar suporte historico do item;
- verificar comparabilidade de unidade;
- conferir consistencia unit_price * quantity vs total_price;
- medir dependencia de tickets altos;
- identificar oportunidades que exigem cautela antes do dashboard.
"""

import sys
from pathlib import Path

import numpy as np
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


def main():
    print("=" * 90)
    print("FASE 13.14.4 - AUDITORIA SAVINGS OPPORTUNITIES | 2026")
    print("=" * 90)

    # ---------------------------------------------------------
    # 1. Savings
    # ---------------------------------------------------------
    print("\n[1/6] Carregando oportunidades...")

    savings_path = (
        OUTPUT_DIR
        / "savings_opportunities_oot_2026.parquet"
    )

    savings = pd.read_parquet(
        savings_path
    )

    print(
        f"Oportunidades: {len(savings):,}"
    )

    # ---------------------------------------------------------
    # 2. Gold
    # ---------------------------------------------------------
    print("\n[2/6] Carregando Gold...")

    gold = load_gold_layer()

    fact = gold["fact_purchase"]
    dim_item = gold["dim_item"]

    df = prepare_baseline_dataset(
        fact
    )

    df = engineer_features(
        df
    )

    splits = split_temporal(df)

    treino_2024 = splits["treino"]
    validacao_2025 = splits["validacao"]
    teste_2026 = splits["teste"]

    historico = pd.concat(
        [
            treino_2024,
            validacao_2025,
        ]
    )

    # ---------------------------------------------------------
    # 3. Suporte historico
    # ---------------------------------------------------------
    print("\n[3/6] Calculando suporte historico...")

    hist_item = (
        historico
        .groupby("item_key")
        .agg(
            n_historico=(
                "unit_price",
                "size",
            ),
            preco_hist_mediana=(
                "unit_price",
                "median",
            ),
            preco_hist_p25=(
                "unit_price",
                lambda s: s.quantile(0.25),
            ),
            preco_hist_p75=(
                "unit_price",
                lambda s: s.quantile(0.75),
            ),
        )
        .reset_index()
    )

    savings = savings.merge(
        hist_item,
        on="item_key",
        how="left",
        validate="many_to_one",
    )

    # ---------------------------------------------------------
    # 4. Metadados de qualidade
    # ---------------------------------------------------------
    print("\n[4/6] Reanexando qualidade e descricao...")

    metadata_cols = [
    "unit_flag",
    "resultado_conflitante",
    ]

    metadata = (
        teste_2026[
            metadata_cols
        ]
        .copy()
    )

    metadata["observation_id"] = (
        metadata.index
    )

    savings = savings.merge(
        metadata,
        on="observation_id",
        how="left",
        validate="one_to_one",
    )

    item_lookup = (
        dim_item[
            [
                "item_key",
                "descricao_resumida_amostra",
                "material_ou_servico_nome",
            ]
        ]
        .drop_duplicates(
            "item_key"
        )
    )

    savings = savings.merge(
        item_lookup,
        on="item_key",
        how="left",
        validate="many_to_one",
    )

    # ---------------------------------------------------------
    # 5. Flags de auditoria
    # ---------------------------------------------------------
    print("\n[5/6] Criando flags de cautela...")

    savings["valor_calculado"] = (
        savings["unit_price"]
        * savings["quantity"]
    )

    denominador_total = (
        savings["total_price"]
        .abs()
        .replace(0, np.nan)
    )

    savings["dif_total_pct"] = (
        100
        * (
            savings["valor_calculado"]
            - savings["total_price"]
        )
        .abs()
        / denominador_total
    )

    savings["saving_share_total_pct"] = (
        100
        * savings["potential_saving"]
        / denominador_total
    )

    savings["price_vs_hist_median_x"] = (
        savings["unit_price"]
        / savings[
            "preco_hist_mediana"
        ].replace(0, np.nan)
    )

    savings["flag_pouco_historico"] = (
        savings["n_historico"] < 5
    )

    savings["flag_unidade_nao_comparavel"] = (
        savings["unit_flag"]
        != "unit_comparable"
    )

    savings["flag_inconsistencia_total"] = (
        savings["dif_total_pct"] > 1.0
    )

    savings["flag_resultado_conflitante"] = (
        savings["resultado_conflitante"]
        .fillna(False)
        .astype(bool)
    )

    flags = [
        "ticket_alto_cautela",
        "flag_pouco_historico",
        "flag_unidade_nao_comparavel",
        "flag_inconsistencia_total",
        "flag_resultado_conflitante",
    ]

    savings["n_flags_cautela"] = (
        savings[flags]
        .fillna(False)
        .astype(int)
        .sum(axis=1)
    )

    # ---------------------------------------------------------
    # 6. Resultados
    # ---------------------------------------------------------
    print("\n[6/6] Consolidando auditoria...")

    total_savings = (
        savings["potential_saving"].sum()
    )

    sem_ticket_alto = savings[
        ~savings["ticket_alto_cautela"]
    ]

    sem_flags = savings[
        savings["n_flags_cautela"] == 0
    ]

    print("\n" + "=" * 90)
    print("RESUMO DE CONFIABILIDADE")
    print("=" * 90)

    print(
        f"Oportunidades totais:                "
        f"{len(savings):,}"
    )

    print(
        f"Potential Savings bruto:             "
        f"R$ {total_savings:,.2f}"
    )

    print(
        f"Ticket alto:                         "
        f"{int(savings['ticket_alto_cautela'].sum()):,}"
    )

    print(
        f"Pouco historico (<5):                "
        f"{int(savings['flag_pouco_historico'].sum()):,}"
    )

    print(
        f"Unidade nao comparavel:              "
        f"{int(savings['flag_unidade_nao_comparavel'].sum()):,}"
    )

    print(
        f"Inconsistencia total >1%:            "
        f"{int(savings['flag_inconsistencia_total'].sum()):,}"
    )

    print(
        f"Resultado conflitante:               "
        f"{int(savings['flag_resultado_conflitante'].sum()):,}"
    )

    print(
        f"Sem nenhuma flag de cautela:         "
        f"{len(sem_flags):,}"
    )

    print(
        f"Savings sem ticket alto:             "
        f"R$ {sem_ticket_alto['potential_saving'].sum():,.2f}"
    )

    print(
        f"Savings sem nenhuma flag:            "
        f"R$ {sem_flags['potential_saving'].sum():,.2f}"
    )

    print("\n" + "=" * 90)
    print("TOP 30 — AUDITORIA")
    print("=" * 90)

    colunas = [
        "purchase_item_id",
        "descricao_resumida_amostra",
        "categoria_relevante",
        "nome_fornecedor",
        "unit_price",
        "preco_esperado",
        "quantity",
        "total_price",
        "potential_saving",
        "n_historico",
        "preco_hist_mediana",
        "price_vs_hist_median_x",
        "unit_flag",
        "ticket_alto_cautela",
        "n_flags_cautela",
    ]

    print(
        savings[
            colunas
        ]
        .head(30)
        .to_string(
            index=False
        )
    )

    output_path = (
        OUTPUT_DIR
        / "savings_audit_oot_2026.csv"
    )

    savings.to_csv(
        output_path,
        index=False,
    )

    print("\nARQUIVO SALVO")
    print(output_path)

    print("\n" + "=" * 90)
    print("FIM — AUDITORIA SAVINGS")
    print("=" * 90)


if __name__ == "__main__":
    main()