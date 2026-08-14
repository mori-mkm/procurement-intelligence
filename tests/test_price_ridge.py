import numpy as np
import pandas as pd

from src.analytics.price_ridge import (
    FEATURES,
    prepare_ridge_features,
    train_ridge_model,
    predict_ridge_model,
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


def test_prepare_ridge_features_keeps_expected_columns():
    df = build_sample()

    X = prepare_ridge_features(df)

    assert list(X.columns) == FEATURES

    for col in [
        "item_key",
        "categoria_relevante",
        "unidade_orgao_uf_sigla",
        "unit_flag",
    ]:
        assert X[col].map(type).eq(str).all()


def test_ridge_train_and_predict():
    df = build_sample()

    model = train_ridge_model(df)

    pred = predict_ridge_model(
        model,
        df,
    )

    assert len(pred) == len(df)
    assert np.isfinite(pred).all()


def test_ridge_predicts_unseen_item_without_error():
    treino = build_sample()

    model = train_ridge_model(treino)

    validacao = treino.iloc[:2].copy()

    validacao.loc[
        validacao.index[0],
        "item_key",
    ] = "produto_totalmente_novo"

    pred = predict_ridge_model(
        model,
        validacao,
    )

    assert len(pred) == 2
    assert np.isfinite(pred).all()