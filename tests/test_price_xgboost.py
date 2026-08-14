import numpy as np
import pandas as pd

from src.analytics.price_xgboost import (
    FEATURES,
    fit_category_levels,
    prepare_xgboost_features,
    train_xgboost_model,
    predict_xgboost_model,
)

def build_train_sample():
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


def test_unseen_category_is_mapped_to_missing():
    treino = build_train_sample()

    levels = fit_category_levels(treino)

    validacao = treino.iloc[[0]].copy()
    validacao["item_key"] = "produto_novo"

    X = prepare_xgboost_features(
        validacao,
        levels,
    )

    assert list(X.columns) == FEATURES

    # Produto novo nao pode ganhar um codigo categorico
    # arbitrario. Deve seguir como missing.
    assert pd.isna(
        X["item_key"].iloc[0]
    )

    for col in [
        "item_key",
        "categoria_relevante",
        "unidade_orgao_uf_sigla",
        "unit_flag",
    ]:
        assert isinstance(
            X[col].dtype,
            pd.CategoricalDtype,
        )


def test_xgboost_train_and_predict_with_unseen_item():
    treino = build_train_sample()

    fitted = train_xgboost_model(
        treino,
        model_params={
            "n_estimators": 10,
            "max_depth": 3,
        },
    )

    validacao = treino.iloc[:2].copy()

    validacao.loc[
        validacao.index[0],
        "item_key",
    ] = "produto_novo"

    pred = predict_xgboost_model(
        fitted,
        validacao,
    )

    assert len(pred) == len(validacao)
    assert np.isfinite(pred).all()