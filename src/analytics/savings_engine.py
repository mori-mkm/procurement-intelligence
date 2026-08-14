"""
Modulo 2 - Price Intelligence: Savings Opportunity Engine. Fase 10.
Formula do brief original (Fase 0): max(observado-esperado,0) x quantidade.
Nao afirma sobrepreco -- gera ranking de oportunidades para revisao.
"""
from __future__ import annotations

from typing import Any

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
