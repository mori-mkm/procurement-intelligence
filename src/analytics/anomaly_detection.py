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


def calibrate_anomaly_threshold(
    errors: pd.DataFrame,
    percentil: float = 95.0,
    known_only: bool = True,
) -> float:
    """
    Calibra um limiar fixo de anomalia usando abs_log_error.

    O threshold deve ser aprendido em uma amostra de calibracao
    anterior ao conjunto no qual sera aplicado.

    Por padrao, somente itens conhecidos entram na calibracao.
    """

    if not 0 < percentil <= 100:
        raise ValueError(
            "percentil precisa estar no intervalo (0, 100]"
        )

    if "abs_log_error" not in errors.columns:
        raise ValueError(
            "Coluna obrigatoria ausente: abs_log_error"
        )

    if known_only:
        if "is_known_item" not in errors.columns:
            raise ValueError(
                "is_known_item e obrigatorio quando known_only=True"
            )

        avaliavel = (
            errors["is_known_item"]
            .fillna(False)
            .astype(bool)
        )

    else:
        avaliavel = pd.Series(
            True,
            index=errors.index,
        )

    valores = (
        errors.loc[
            avaliavel,
            "abs_log_error",
        ]
        .dropna()
    )

    if valores.empty:
        raise ValueError(
            "Nao existem observacoes avaliaveis para calibrar o threshold"
        )

    threshold = valores.quantile(
        percentil / 100.0
    )

    return float(threshold)


def flag_price_anomalies_frozen(
    errors: pd.DataFrame,
    threshold: float,
    known_only: bool = True,
) -> pd.DataFrame:
    """
    Aplica um threshold previamente calibrado.

    Esta funcao NAO recalcula percentis no conjunto recebido.
    """

    if threshold < 0:
        raise ValueError(
            "threshold nao pode ser negativo"
        )

    required = {
        "log_unit_price_real",
        "log_unit_price_pred",
        "unit_price",
        "unit_price_pred",
        "abs_log_error",
    }

    missing = required - set(errors.columns)

    if missing:
        raise ValueError(
            "Colunas obrigatorias ausentes: "
            f"{sorted(missing)}"
        )

    df = errors.copy()

    if known_only:
        if "is_known_item" not in df.columns:
            raise ValueError(
                "is_known_item e obrigatorio quando known_only=True"
            )

        avaliavel = (
            df["is_known_item"]
            .fillna(False)
            .astype(bool)
        )

    else:
        avaliavel = pd.Series(
            True,
            index=df.index,
        )

    df["residuo_log"] = (
        df["log_unit_price_real"]
        - df["log_unit_price_pred"]
    )

    # Mantem compatibilidade com Savings Engine.
    df["preco_esperado"] = (
        df["unit_price_pred"]
    )

    denominador = (
        df["preco_esperado"]
        .replace(0, np.nan)
    )

    df["price_deviation_pct"] = (
        100
        * (
            df["unit_price"]
            - df["preco_esperado"]
        )
        / denominador
    )

    df["anomaly_threshold_abs_log"] = float(
        threshold
    )

    df["is_price_anomaly"] = (
        avaliavel
        & (
            df["abs_log_error"]
            >= threshold
        )
    )

    df["anomaly_direction"] = np.select(
        [
            (
                df["is_price_anomaly"]
                & (df["residuo_log"] > 0)
            ),
            (
                df["is_price_anomaly"]
                & (df["residuo_log"] <= 0)
            ),
        ],
        [
            "acima_do_esperado",
            "abaixo_do_esperado",
        ],
        default=np.where(
            avaliavel,
            "normal",
            "nao_avaliavel",
        ),
    )

    return df