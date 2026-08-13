"""
Modulo 2 - Price Intelligence: baseline de preco (mediana por item_key).
Fase 7. Ver ADR-0003 (split temporal), ADR-0015 (escopo de item_key).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.analytics.spend_analytics import flag_extreme_by_global_median

MIN_TRANSACOES_BASELINE_CONFIAVEL = 5

ANO_TREINO = 2024
ANO_VALIDACAO = 2025
ANO_TESTE = 2026


def prepare_baseline_dataset(df_fact: pd.DataFrame) -> pd.DataFrame:
    """Aplica o escopo definido no ADR-0015 antes de qualquer calculo de
    baseline: (1) so categorias relevantes (ADR-0009); (2) exclui
    outliers de valor, calculados DENTRO do universo ja filtrado por
    categoria -- nao no fact inteiro (correcao: a mediana global de
    referencia precisa ser do mesmo universo que sera analisado, senao
    "extremo" e definido contra um universo diferente do que estamos
    medindo, distorcendo o resultado); (3) adiciona coluna 'ano'.
    """
    df = df_fact[df_fact["categoria_relevante"].notna()].copy()

    is_outlier = df["is_value_outlier"].fillna(False) if "is_value_outlier" in df.columns else pd.Series(False, index=df.index)
    df = df[~is_outlier]

    if "total_price" in df.columns:
        is_extremo = flag_extreme_by_global_median(df)
        df = df[~is_extremo.reindex(df.index).fillna(False)]

    df["ano"] = df["date_key"] // 10000
    return df


def split_temporal(df: pd.DataFrame, ano_col: str = "ano") -> dict[str, pd.DataFrame]:
    """Split temporal conforme ADR-0003: treino=2024, validacao=2025,
    teste=2026 (parcial). Nao usa random split -- vazamento temporal
    invalidaria qualquer metrica (Fase 0, principio metodologico)."""
    return {
        "treino": df[df[ano_col] == ANO_TREINO].copy(),
        "validacao": df[df[ano_col] == ANO_VALIDACAO].copy(),
        "teste": df[df[ano_col] == ANO_TESTE].copy(),
    }


def compute_median_baseline(
    df_treino: pd.DataFrame,
    item_col: str = "item_key",
    price_col: str = "unit_price",
    min_transacoes: int = MIN_TRANSACOES_BASELINE_CONFIAVEL,
) -> pd.DataFrame:
    """Baseline = mediana de unit_price por item_key, calculada SOMENTE
    com df_treino (ADR-0003). item_key com menos de min_transacoes NO
    TREINO recebe baseline_confiavel=False (ADR-0015)."""
    agg = df_treino.groupby(item_col)[price_col].agg(
        preco_esperado="median",
        n_transacoes_treino="size",
    )
    agg["baseline_confiavel"] = agg["n_transacoes_treino"] >= min_transacoes
    return agg.reset_index()


def evaluate_baseline(
    df_avaliacao: pd.DataFrame,
    baseline: pd.DataFrame,
    item_col: str = "item_key",
    price_col: str = "unit_price",
    only_confiavel: bool = True,
) -> dict[str, Any]:
    """Aplica o baseline (calculado no treino) sobre um conjunto de
    avaliacao (validacao ou teste) e mede erro. item_key sem baseline
    (nunca visto no treino) fica sem previsao -- reportado como cobertura,
    nao como erro.

    only_confiavel=True (default): avalia so item_key com
    baseline_confiavel=True (ADR-0015).
    """
    baseline_usado = baseline[baseline["baseline_confiavel"]] if only_confiavel else baseline

    df = df_avaliacao.merge(
        baseline_usado[[item_col, "preco_esperado"]], on=item_col, how="left"
    )

    n_total = len(df)
    n_com_baseline = int(df["preco_esperado"].notna().sum())

    avaliavel = df[df["preco_esperado"].notna()].copy()
    if avaliavel.empty:
        return {
            "n_transacoes_total": n_total,
            "n_transacoes_com_baseline": 0,
            "pct_cobertura": 0.0,
            "mae": None, "rmse": None, "mape": None,
        }

    erro = avaliavel[price_col] - avaliavel["preco_esperado"]
    erro_abs = erro.abs()
    erro_pct = erro_abs / avaliavel[price_col].replace(0, np.nan)

    mae = erro_abs.mean()
    rmse = np.sqrt((erro**2).mean())
    mape = 100 * erro_pct.mean()
    mape_mediana = 100 * erro_pct.median()

    return {
        "n_transacoes_total": n_total,
        "n_transacoes_com_baseline": n_com_baseline,
        "pct_cobertura": round(100 * n_com_baseline / n_total, 2) if n_total else 0.0,
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "mape_media": round(float(mape), 2),
        "mape_mediana": round(float(mape_mediana), 2),
    }


def build_price_baseline_report(df_fact: pd.DataFrame) -> dict[str, Any]:
    """Pipeline completo da Fase 7."""
    df_preparado = prepare_baseline_dataset(df_fact)
    splits = split_temporal(df_preparado)

    baseline = compute_median_baseline(splits["treino"])

    resultado_validacao = evaluate_baseline(splits["validacao"], baseline)
    resultado_teste = evaluate_baseline(splits["teste"], baseline)

    return {
        "n_transacoes_treino": len(splits["treino"]),
        "n_transacoes_validacao": len(splits["validacao"]),
        "n_transacoes_teste": len(splits["teste"]),
        "n_itens_com_baseline_confiavel": int(baseline["baseline_confiavel"].sum()),
        "n_itens_total_no_treino": len(baseline),
        "avaliacao_validacao": resultado_validacao,
        "avaliacao_teste": resultado_teste,
    }
