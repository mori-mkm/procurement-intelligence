"""
Fase 13 - XGBoost challenger para modelagem de preco.

Usa as mesmas features conceituais e o mesmo target dos demais modelos.

Treino: 2024
Selecao: 2025
Teste final OOT: 2026

Categorias novas em inferencia sao explicitamente mapeadas para
__UNKNOWN__, evitando dependencia de categorias futuras.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from xgboost import XGBRegressor

from src.analytics.price_ml import (
    FEATURES_CATEGORICAS,
    FEATURES_NUMERICAS,
)


FEATURES = FEATURES_CATEGORICAS + FEATURES_NUMERICAS



DEFAULT_XGBOOST_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 6,
    "objective": "reg:squarederror",
    "tree_method": "hist",
    "enable_categorical": True,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
}


@dataclass
class XGBoostPriceModel:
    model: XGBRegressor
    category_levels: dict[str, list[str]]


def fit_category_levels(
    treino: pd.DataFrame,
) -> dict[str, list[str]]:
    """
    Aprende o vocabulario categorico exclusivamente a partir do treino.

    Apenas categorias realmente observadas em treino fazem parte
    do vocabulario.

    Valores ausentes e categorias unseen em inferencia serao
    representados como NaN.
    """

    levels = {}

    for col in FEATURES_CATEGORICAS:
        if col not in treino.columns:
            raise ValueError(
                f"Feature categorica ausente: {col}"
            )

        values = (
            treino[col]
            .astype("string")
            .dropna()
            .astype(str)
        )

        levels[col] = sorted(
            values.unique().tolist()
        )

    return levels


def prepare_xgboost_features(
    df: pd.DataFrame,
    category_levels: dict[str, list[str]],
) -> pd.DataFrame:
    """
    Prepara features usando vocabulario aprendido exclusivamente
    no treino.

    Categorias nao observadas durante treinamento sao convertidas
    para missing (NaN), permitindo que o XGBoost utilize o missing
    branch aprendido pelas arvores.
    """

    missing = set(FEATURES) - set(df.columns)

    if missing:
        raise ValueError(
            f"Features obrigatorias ausentes: {sorted(missing)}"
        )

    X = df[FEATURES].copy()

    for col in FEATURES_CATEGORICAS:
        if col not in category_levels:
            raise ValueError(
                f"Vocabulario ausente para feature: {col}"
            )

        categorias = category_levels[col]

        values = X[col].astype("string")

        # Categoria realmente nova em inferencia:
        # trata como missing em vez de criar um nivel que nunca
        # apareceu durante o treinamento.
        values = values.where(
            values.isna() | values.isin(categorias),
            pd.NA,
        )

        dtype = pd.CategoricalDtype(
            categories=categorias
        )

        X[col] = values.astype(dtype)

    for col in FEATURES_NUMERICAS:
        X[col] = pd.to_numeric(
            X[col],
            errors="coerce",
        )

    return X


def train_xgboost_model(
    treino: pd.DataFrame,
    model_params: dict[str, Any] | None = None,
) -> XGBoostPriceModel:
    """
    Treina XGBRegressor com log_unit_price como target.
    """

    if "log_unit_price" not in treino.columns:
        raise ValueError(
            "Coluna target 'log_unit_price' ausente"
        )

    category_levels = fit_category_levels(treino)

    X_train = prepare_xgboost_features(
        treino,
        category_levels,
    )

    y_train = treino["log_unit_price"].astype(float)

    params = DEFAULT_XGBOOST_PARAMS.copy()

    if model_params:
        params.update(model_params)

    model = XGBRegressor(**params)

    model.fit(
        X_train,
        y_train,
    )

    return XGBoostPriceModel(
        model=model,
        category_levels=category_levels,
    )


def predict_xgboost_model(
    fitted: XGBoostPriceModel,
    df: pd.DataFrame,
):
    """
    Gera previsoes no espaco logaritmico usando o vocabulario
    aprendido exclusivamente durante treinamento.
    """

    X = prepare_xgboost_features(
        df,
        fitted.category_levels,
    )

    return fitted.model.predict(X)