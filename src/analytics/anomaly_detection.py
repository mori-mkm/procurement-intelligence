"""
Modulo 2 - Price Intelligence: deteccao de anomalia via percentil de residuo.
Fase 9. Usa o modelo ML (Fase 8), nao o baseline -- cobertura 100%.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.analytics.price_ml import FEATURES_CATEGORICAS, FEATURES_NUMERICAS


def compute_residuals(df: pd.DataFrame, modelo) -> pd.DataFrame:
    """Calcula preco previsto e residuo (log_real - log_previsto) e
    price_deviation_pct ((observado-esperado)/esperado), conforme o brief
    original da Fase 0. Nao decide sozinho o que e anomalia -- so calcula."""
    df = df.copy()
    features = FEATURES_CATEGORICAS + FEATURES_NUMERICAS
    log_pred = modelo.predict(df[features])
    df["preco_esperado"] = np.exp(log_pred)
    df["residuo_log"] = np.log(df["unit_price"].clip(lower=1e-6)) - log_pred
    df["price_deviation_pct"] = 100 * (df["unit_price"] - df["preco_esperado"]) / df["preco_esperado"]
    return df


def flag_price_anomalies(df: pd.DataFrame, percentil: float = 95.0, item_col: str = "item_key") -> pd.DataFrame:
    """Flag de possivel anomalia: |residuo_log| acima do percentil
    informado. Nao afirma sobrepreco/fraude -- so sinaliza desvio
    estatistico para revisao humana.

    Exclui item_key nulo (item nunca visto no treino, categoria vira NaN
    no LightGBM -- previsao nesse caso nao e confiavel o suficiente para
    virar anomalia; achado real, Fase 9) do calculo do limiar e da flag.
    """
    df = df.copy()
    avaliavel = df[item_col].notna()

    limiar = df.loc[avaliavel, "residuo_log"].abs().quantile(percentil / 100)
    df["is_price_anomaly"] = avaliavel & (df["residuo_log"].abs() >= limiar)
    df["anomaly_direction"] = np.select(
        [df["is_price_anomaly"] & (df["residuo_log"] > 0), df["is_price_anomaly"] & (df["residuo_log"] <= 0)],
        ["acima_do_esperado", "abaixo_do_esperado"],
        default=np.where(avaliavel, "normal", "nao_avaliavel"),
    )
    return df


def summarize_anomalies(df: pd.DataFrame) -> dict[str, Any]:
    anomalias = df[df["is_price_anomaly"]]
    return {
        "n_transacoes_avaliadas": len(df),
        "n_anomalias": len(anomalias),
        "pct_anomalias": round(100 * len(anomalias) / len(df), 2) if len(df) else 0.0,
        "n_acima_do_esperado": int((anomalias["anomaly_direction"] == "acima_do_esperado").sum()),
        "n_abaixo_do_esperado": int((anomalias["anomaly_direction"] == "abaixo_do_esperado").sum()),
        "spend_em_anomalias_acima": round(
            float(anomalias.loc[anomalias["anomaly_direction"] == "acima_do_esperado", "total_price"].sum()), 2
        ) if "total_price" in df.columns else None,
    }
