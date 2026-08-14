"""
Fase 13 - Ridge Regression como modelo supervisionado simples.

Objetivo:
- criar um benchmark linear regularizado;
- usar exatamente as mesmas features conceituais dos modelos de boosting;
- treinar em 2024;
- selecionar em 2025;
- manter 2026 intocado.

Categoricas:
    One-Hot Encoding

Numerica:
    StandardScaler

Target:
    log_unit_price
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)

from src.analytics.price_ml import (
    FEATURES_CATEGORICAS,
    FEATURES_NUMERICAS,
)


FEATURES = FEATURES_CATEGORICAS + FEATURES_NUMERICAS

MISSING_CATEGORY = "__MISSING__"


DEFAULT_RIDGE_PARAMS = {
    "alpha": 1.0,
    "solver": "lsqr",
}


def prepare_ridge_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepara as features do Ridge.

    Categoricas sao convertidas para string.
    Ausentes recebem marcador explicito.

    Categorias novas em validacao serao tratadas posteriormente
    pelo OneHotEncoder(handle_unknown='ignore').
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
            .fillna(MISSING_CATEGORY)
            .astype(str)
        )

    for col in FEATURES_NUMERICAS:
        X[col] = pd.to_numeric(
            X[col],
            errors="coerce",
        )

    return X


def build_ridge_pipeline(
    model_params: dict[str, Any] | None = None,
) -> Pipeline:
    """
    Constroi pipeline de preprocessing + Ridge.

    O OneHotEncoder permanece sparse para evitar materializar uma
    matriz densa de alta dimensionalidade devido ao item_key.
    """

    categorical_transformer = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=True,
        dtype=float,
    )

    numeric_transformer = StandardScaler(
        with_mean=False,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                categorical_transformer,
                FEATURES_CATEGORICAS,
            ),
            (
                "numeric",
                numeric_transformer,
                FEATURES_NUMERICAS,
            ),
        ],
        sparse_threshold=1.0,
    )

    params = DEFAULT_RIDGE_PARAMS.copy()

    if model_params:
        params.update(model_params)

    model = Ridge(**params)

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def train_ridge_model(
    treino: pd.DataFrame,
    model_params: dict[str, Any] | None = None,
) -> Pipeline:
    """
    Treina Ridge usando log_unit_price como target.
    """

    if "log_unit_price" not in treino.columns:
        raise ValueError(
            "Coluna target 'log_unit_price' ausente"
        )

    X_train = prepare_ridge_features(treino)
    y_train = treino["log_unit_price"].astype(float)

    model = build_ridge_pipeline(
        model_params=model_params,
    )

    model.fit(
        X_train,
        y_train,
    )

    return model


def predict_ridge_model(
    model: Pipeline,
    df: pd.DataFrame,
):
    """
    Gera previsoes no espaco logaritmico.
    """

    X = prepare_ridge_features(df)

    return model.predict(X)