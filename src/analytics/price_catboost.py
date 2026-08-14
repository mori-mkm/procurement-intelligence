"""
Fase 13 - CatBoost challenger para modelagem de preco.

O modelo utiliza o mesmo target e o mesmo conjunto conceitual de features
do LightGBM, mas preserva o tratamento nativo de variaveis categoricas
do CatBoost.

Treino: 2024
Selecao: 2025
Teste final OOT: 2026
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from catboost import CatBoostRegressor

from src.analytics.price_ml import (
    FEATURES_CATEGORICAS,
    FEATURES_NUMERICAS,
)


FEATURES = FEATURES_CATEGORICAS + FEATURES_NUMERICAS


DEFAULT_CATBOOST_PARAMS = {
    "iterations": 300,
    "learning_rate": 0.05,
    "depth": 6,
    "loss_function": "RMSE",
    "random_seed": 42,
    "verbose": False,
    "allow_writing_files": False,
    "thread_count": -1,
}


def prepare_catboost_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepara as features para o CatBoost.

    Categoricas sao convertidas para string e valores ausentes recebem
    um marcador explicito.

    Numericas sao convertidas para tipo numerico.
    """

    missing = set(FEATURES) - set(df.columns)

    if missing:
        raise ValueError(
            f"Features obrigatorias ausentes: {sorted(missing)}"
        )

    X = df[FEATURES].copy()

    for col in FEATURES_CATEGORICAS:
        X[col] = (
            X[col]
            .astype("string")
            .fillna("__MISSING__")
            .astype(str)
        )

    for col in FEATURES_NUMERICAS:
        X[col] = pd.to_numeric(
            X[col],
            errors="coerce",
        )

    return X


def train_catboost_model(
    treino: pd.DataFrame,
    model_params: dict[str, Any] | None = None,
) -> CatBoostRegressor:
    """
    Treina CatBoostRegressor usando log_unit_price como target.
    """

    if "log_unit_price" not in treino.columns:
        raise ValueError(
            "Coluna target 'log_unit_price' ausente"
        )

    X_train = prepare_catboost_features(treino)
    y_train = treino["log_unit_price"].astype(float)

    params = DEFAULT_CATBOOST_PARAMS.copy()

    if model_params:
        params.update(model_params)

    model = CatBoostRegressor(**params)

    model.fit(
        X_train,
        y_train,
        cat_features=FEATURES_CATEGORICAS,
    )

    return model


def predict_catboost_model(
    model: CatBoostRegressor,
    df: pd.DataFrame,
):
    """
    Gera previsoes no espaco logaritmico.
    """

    X = prepare_catboost_features(df)

    return model.predict(X)