"""
Modulo 2 - Price Intelligence: Savings Opportunity Engine. Fase 10.
Formula do brief original (Fase 0): max(observado-esperado,0) x quantidade.
Nao afirma sobrepreco -- gera ranking de oportunidades para revisao.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

TICKET_ALTO_LIMIAR = 100_000.0  # acima disso, cautela extra (Fase 9, nota de interpretacao)


def compute_savings_opportunity(df_anomalias: pd.DataFrame) -> pd.DataFrame:
    """Calcula savings potencial so para anomalias acima do esperado.
    Flag de cautela para ticket alto -- nao remove, so sinaliza (mesmo
    padrao nao-destrutivo do projeto inteiro)."""
    df = df_anomalias[df_anomalias["anomaly_direction"] == "acima_do_esperado"].copy()
    df["potential_saving"] = (df["unit_price"] - df["preco_esperado"]).clip(lower=0) * df["quantity"]
    df["ticket_alto_cautela"] = df["unit_price"] >= TICKET_ALTO_LIMIAR
    df["rotulo"] = "Potential Savings Opportunity"
    return df.sort_values("potential_saving", ascending=False)


def rank_savings_by_category(df_savings: pd.DataFrame, category_col: str = "categoria_relevante") -> pd.DataFrame:
    """Ranking de categorias por potencial de savings agregado -- responde
    "onde priorizar esforco de negociacao" (Fase 0, Modulo 1)."""
    agg = df_savings.groupby(category_col).agg(
        savings_potencial_total=("potential_saving", "sum"),
        n_oportunidades=("potential_saving", "size"),
        n_ticket_alto_cautela=("ticket_alto_cautela", "sum"),
    )
    return agg.sort_values("savings_potencial_total", ascending=False).reset_index()


def summarize_savings(df_savings: pd.DataFrame) -> dict[str, Any]:
    sem_cautela = df_savings[~df_savings["ticket_alto_cautela"]]
    return {
        "savings_potencial_total": round(float(df_savings["potential_saving"].sum()), 2),
        "savings_potencial_excluindo_ticket_alto": round(float(sem_cautela["potential_saving"].sum()), 2),
        "n_oportunidades_total": len(df_savings),
        "n_oportunidades_ticket_alto_cautela": int(df_savings["ticket_alto_cautela"].sum()),
    }


def classify_savings_priority(
    df_savings: pd.DataFrame,
    high_share: float = 0.70,
    medium_share: float = 0.90,
) -> pd.DataFrame:
    """
    Prioriza oportunidades pelo impacto financeiro acumulado.

    Alta:
        oportunidades necessarias para cobrir aproximadamente
        os primeiros 70% do potential saving.

    Media:
        proximas oportunidades ate aproximadamente 90%.

    Baixa:
        cauda restante.

    A classificacao usa impacto financeiro, nao tamanho do erro
    do modelo.
    """

    if not 0 < high_share < medium_share <= 1:
        raise ValueError(
            "Esperado: 0 < high_share < medium_share <= 1"
        )

    if "potential_saving" not in df_savings.columns:
        raise ValueError(
            "Coluna obrigatoria ausente: potential_saving"
        )

    df = (
        df_savings
        .sort_values(
            "potential_saving",
            ascending=False,
        )
        .copy()
    )

    if df.empty:
        df["savings_cumulative_share"] = pd.Series(
            dtype=float
        )
        df["priority"] = pd.Series(
            dtype=str
        )
        return df

    total = float(
        df["potential_saving"].sum()
    )

    if total <= 0:
        df["savings_cumulative_share"] = 0.0
        df["priority"] = "Baixa"
        return df

    cumulative = (
        df["potential_saving"].cumsum()
    )

    # Share acumulado ANTES da oportunidade atual.
    # Assim, a oportunidade que cruza o limite continua
    # pertencendo ao grupo que ajuda a atingir aquele limite.
    share_before = (
        cumulative
        - df["potential_saving"]
    ) / total

    df["savings_cumulative_share"] = (
        cumulative / total
    )

    df["priority"] = np.select(
        [
            share_before < high_share,
            share_before < medium_share,
        ],
        [
            "Alta",
            "Media",
        ],
        default="Baixa",
    )

    return df


def classify_savings_confidence(
    df_savings: pd.DataFrame,
) -> pd.DataFrame:
    """
    Classifica a confiabilidade da oportunidade financeira.

    Alta:
        unidade comparavel, historico suficiente,
        sem inconsistencias, sem conflito e sem ticket alto.

    Revisao Alto Valor:
        qualidade tecnica adequada, mas ticket alto exige
        revisao manual antes de uso executivo.

    Baixa:
        existe problema de comparabilidade, pouco historico,
        inconsistencia ou resultado conflitante.
    """

    required = {
        "ticket_alto_cautela",
        "flag_pouco_historico",
        "flag_unidade_nao_comparavel",
        "flag_inconsistencia_total",
        "flag_resultado_conflitante",
    }

    missing = required - set(
        df_savings.columns
    )

    if missing:
        raise ValueError(
            "Colunas obrigatorias ausentes: "
            f"{sorted(missing)}"
        )

    df = df_savings.copy()

    quality_flags = [
        "flag_pouco_historico",
        "flag_unidade_nao_comparavel",
        "flag_inconsistencia_total",
        "flag_resultado_conflitante",
    ]

    has_quality_issue = (
        df[quality_flags]
        .fillna(False)
        .astype(bool)
        .any(axis=1)
    )

    high_ticket = (
        df["ticket_alto_cautela"]
        .fillna(False)
        .astype(bool)
    )

    df["confidence_tier"] = np.select(
        [
            ~has_quality_issue & ~high_ticket,
            ~has_quality_issue & high_ticket,
        ],
        [
            "Alta",
            "Revisao Alto Valor",
        ],
        default="Baixa",
    )

    return df