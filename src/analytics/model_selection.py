"""
Fase 13 - Model Validation & Selection.

Funcoes compartilhadas para avaliar candidatos de modelagem de preco
com a mesma regua metodologica.

IMPORTANTE:
- treino: 2024
- validacao / selecao: 2025
- teste final OOT: 2026
- 2026 nao deve participar da selecao do modelo.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd


def build_prediction_errors(
    df: pd.DataFrame,
    log_pred: np.ndarray,
    model_name: str,
    train_item_keys: Iterable[str] | None = None,
) -> pd.DataFrame:
    """
    Constroi tabela transacional de erros.

    Essa tabela sera usada posteriormente para:
    - comparar modelos na mesma amostra;
    - separar itens conhecidos vs unseen;
    - bootstrap pareado por item_key.
    """

    required = {"unit_price", "item_key"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Colunas obrigatorias ausentes: {sorted(missing)}"
        )

    if len(df) != len(log_pred):
        raise ValueError(
            "df e log_pred precisam ter o mesmo numero de linhas"
        )

    result = df[["item_key", "unit_price"]].copy()

    # Preserva a identidade da observacao para comparacoes pareadas
    # entre modelos na mesma amostra de validacao.
    result["observation_id"] = df.index

    result["model"] = model_name
    result["log_unit_price_real"] = np.log(
        result["unit_price"].clip(lower=1e-6)
    )
    result["log_unit_price_pred"] = np.asarray(log_pred)

    result["unit_price_pred"] = np.exp(
        result["log_unit_price_pred"]
    )

    result["abs_log_error"] = (
        result["log_unit_price_real"]
        - result["log_unit_price_pred"]
    ).abs()

    result["squared_log_error"] = (
        result["log_unit_price_real"]
        - result["log_unit_price_pred"]
    ) ** 2

    result["abs_error"] = (
        result["unit_price"]
        - result["unit_price_pred"]
    ).abs()

    result["abs_pct_error"] = (
        100
        * result["abs_error"]
        / result["unit_price"].replace(0, np.nan)
    )

    if train_item_keys is not None:
        train_item_keys = set(train_item_keys)

        result["is_known_item"] = (
            result["item_key"].isin(train_item_keys)
        )

    return result


def evaluate_prediction_errors(
    errors: pd.DataFrame,
) -> dict[str, Any]:
    """
    Calcula metricas compartilhadas entre os modelos.

    Metrica primaria:
        MAE no log do preco.

    Metricas secundarias:
        RMSE log
        MedAPE
        WAPE
        MAE em reais
        RMSE em reais
    """

    if errors.empty:
        raise ValueError("Tabela de erros vazia")

    required = {
        "unit_price",
        "unit_price_pred",
        "abs_log_error",
        "squared_log_error",
        "abs_error",
        "abs_pct_error",
    }

    missing = required - set(errors.columns)

    if missing:
        raise ValueError(
            f"Colunas obrigatorias ausentes: {sorted(missing)}"
        )

    mae_log = errors["abs_log_error"].mean()

    rmse_log = np.sqrt(
        errors["squared_log_error"].mean()
    )

    medape = errors["abs_pct_error"].median()

    denominator = errors["unit_price"].abs().sum()

    wape = (
        100 * errors["abs_error"].sum() / denominator
        if denominator > 0
        else np.nan
    )

    mae = errors["abs_error"].mean()

    rmse = np.sqrt(
        (
            (
                errors["unit_price"]
                - errors["unit_price_pred"]
            )
            ** 2
        ).mean()
    )

    metrics = {
        "n_transacoes": int(len(errors)),
        "mae_log": float(mae_log),
        "rmse_log": float(rmse_log),
        "medape": float(medape),
        "wape": float(wape),
        "mae": float(mae),
        "rmse": float(rmse),
    }

    if "is_known_item" in errors.columns:
        metrics["known_item_rate"] = float(
            100 * errors["is_known_item"].mean()
        )

        metrics["unseen_item_rate"] = float(
            100 * (~errors["is_known_item"]).mean()
        )

    return metrics