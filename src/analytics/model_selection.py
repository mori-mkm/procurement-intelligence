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


def clustered_paired_bootstrap(
    reference_errors: pd.DataFrame,
    challenger_errors: pd.DataFrame,
    reference_name: str,
    challenger_name: str,
    cluster_col: str = "item_key",
    n_bootstrap: int = 5000,
    confidence: float = 0.95,
    random_state: int = 42,
) -> dict[str, Any]:
    """
    Compara dois modelos por bootstrap pareado agrupado.

    A unidade de reamostragem e o cluster (por padrao, item_key),
    preservando todas as transacoes pertencentes ao item sorteado.

    A estatistica avaliada e:

        delta = MAE_log_challenger - MAE_log_reference

    Interpretacao:
        delta > 0 -> reference apresenta menor erro
        delta < 0 -> challenger apresenta menor erro

    O teste deve ser aplicado exclusivamente sobre a mesma amostra
    de observacoes para os dois modelos.
    """

    if n_bootstrap <= 0:
        raise ValueError(
            "n_bootstrap precisa ser positivo"
        )

    if not 0 < confidence < 1:
        raise ValueError(
            "confidence precisa estar entre 0 e 1"
        )

    required = {
        "observation_id",
        cluster_col,
        "abs_log_error",
    }

    missing_reference = (
        required - set(reference_errors.columns)
    )

    missing_challenger = (
        required - set(challenger_errors.columns)
    )

    if missing_reference:
        raise ValueError(
            "Colunas ausentes no modelo de referencia: "
            f"{sorted(missing_reference)}"
        )

    if missing_challenger:
        raise ValueError(
            "Colunas ausentes no challenger: "
            f"{sorted(missing_challenger)}"
        )

    if reference_errors["observation_id"].duplicated().any():
        raise ValueError(
            "observation_id duplicado no modelo de referencia"
        )

    if challenger_errors["observation_id"].duplicated().any():
        raise ValueError(
            "observation_id duplicado no challenger"
        )

    reference = reference_errors[
        [
            "observation_id",
            cluster_col,
            "abs_log_error",
        ]
    ].copy()

    challenger = challenger_errors[
        [
            "observation_id",
            cluster_col,
            "abs_log_error",
        ]
    ].copy()

    reference = reference.rename(
        columns={
            cluster_col: "cluster_reference",
            "abs_log_error": "reference_error",
        }
    )

    challenger = challenger.rename(
        columns={
            cluster_col: "cluster_challenger",
            "abs_log_error": "challenger_error",
        }
    )

    paired = reference.merge(
        challenger,
        on="observation_id",
        how="inner",
        validate="one_to_one",
    )

    if (
        len(paired) != len(reference_errors)
        or len(paired) != len(challenger_errors)
    ):
        raise ValueError(
            "Os modelos nao possuem exatamente a mesma amostra"
        )

    cluster_reference = (
        paired["cluster_reference"]
        .astype("string")
        .fillna("__MISSING_CLUSTER__")
    )

    cluster_challenger = (
        paired["cluster_challenger"]
        .astype("string")
        .fillna("__MISSING_CLUSTER__")
    )

    if not cluster_reference.equals(
        cluster_challenger
    ):
        raise ValueError(
            f"{cluster_col} desalinhado entre os modelos"
        )

    paired["cluster"] = cluster_reference

    paired["error_diff"] = (
        paired["challenger_error"]
        - paired["reference_error"]
    )

    reference_mae = float(
        paired["reference_error"].mean()
    )

    challenger_mae = float(
        paired["challenger_error"].mean()
    )

    observed_delta = float(
        paired["error_diff"].mean()
    )

    # ---------------------------------------------------------
    # Agrega por cluster antes do bootstrap.
    #
    # Em cada reamostragem sorteamos item_key com reposicao e
    # mantemos todas as transacoes pertencentes ao item sorteado.
    # ---------------------------------------------------------
    cluster_stats = (
        paired
        .groupby(
            "cluster",
            sort=False,
            dropna=False,
        )["error_diff"]
        .agg(["sum", "count"])
    )

    cluster_sums = (
        cluster_stats["sum"]
        .to_numpy(dtype=float)
    )

    cluster_counts = (
        cluster_stats["count"]
        .to_numpy(dtype=float)
    )

    n_clusters = len(cluster_stats)

    if n_clusters < 2:
        raise ValueError(
            "Sao necessarios pelo menos 2 clusters"
        )

    rng = np.random.default_rng(
        random_state
    )

    bootstrap_deltas = np.empty(
        n_bootstrap,
        dtype=float,
    )

    for i in range(n_bootstrap):
        sampled = rng.integers(
            low=0,
            high=n_clusters,
            size=n_clusters,
        )

        sampled_sum = (
            cluster_sums[sampled]
            .sum()
        )

        sampled_count = (
            cluster_counts[sampled]
            .sum()
        )

        bootstrap_deltas[i] = (
            sampled_sum / sampled_count
        )

    alpha = (
        1.0 - confidence
    ) / 2.0

    ci_low = float(
        np.quantile(
            bootstrap_deltas,
            alpha,
        )
    )

    ci_high = float(
        np.quantile(
            bootstrap_deltas,
            1.0 - alpha,
        )
    )

    if ci_low > 0:
        conclusion = "reference_better"
    elif ci_high < 0:
        conclusion = "challenger_better"
    else:
        conclusion = "inconclusive"

    relative_difference_pct = (
        100 * observed_delta / reference_mae
        if reference_mae != 0
        else np.nan
    )

    return {
        "reference_model": reference_name,
        "challenger_model": challenger_name,
        "n_transacoes": int(len(paired)),
        "n_clusters": int(n_clusters),
        "reference_mae_log": reference_mae,
        "challenger_mae_log": challenger_mae,
        "delta_mae_log": observed_delta,
        "relative_difference_pct": float(
            relative_difference_pct
        ),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "confidence": float(confidence),
        "n_bootstrap": int(n_bootstrap),
        "conclusion": conclusion,
    }