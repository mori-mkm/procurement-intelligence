import numpy as np
import pandas as pd

from src.analytics.price_catboost import (
    FEATURES,
    prepare_catboost_features,
    train_catboost_model,
    predict_catboost_model,
)


def build_sample():
    return pd.DataFrame(
        {
            "item_key": [
                "notebook",
                "notebook",
                "monitor",
                "monitor",
                "mouse",
                "mouse",
            ],
            "categoria_relevante": [
                "TI",
                "TI",
                "TI",
                "TI",
                "TI",
                "TI",
            ],
            "unidade_orgao_uf_sigla": [
                "SP",
                "RJ",
                "SP",
                "RJ",
                "SP",
                "RJ",
            ],
            "unit_flag": [
                "UN",
                "UN",
                "UN",
                "UN",
                "UN",
                "UN",
            ],
            "log_quantity": np.log(
                [1, 2, 1, 3, 10, 20]
            ),
            "log_unit_price": np.log(
                [5000, 4800, 1500, 1600, 100, 90]
            ),
        }
    )


def test_prepare_catboost_features_keeps_expected_columns():
    df = build_sample()

    X = prepare_catboost_features(df)

    assert list(X.columns) == FEATURES

    for col in [
        "item_key",
        "categoria_relevante",
        "unidade_orgao_uf_sigla",
        "unit_flag",
    ]:
        assert X[col].map(type).eq(str).all()


def test_catboost_train_and_predict():
    df = build_sample()

    model = train_catboost_model(
        df,
        model_params={
            "iterations": 10,
            "depth": 3,
        },
    )

    pred = predict_catboost_model(
        model,
        df,
    )

    assert len(pred) == len(df)
    assert np.isfinite(pred).all()