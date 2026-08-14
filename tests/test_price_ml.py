import numpy as np
import pandas as pd

from src.analytics.price_ml import engineer_features, align_categorical_dtypes, train_lightgbm_model, evaluate_model


def make_ml_df(n=200, seed=0):
    rng = np.random.default_rng(seed)
    itens = rng.choice(["notebook", "mouse", "cadeira"], n)
    preco_base = {"notebook": 2000.0, "mouse": 50.0, "cadeira": 300.0}
    quantidade = rng.integers(1, 20, n)
    preco = np.array([preco_base[i] for i in itens]) * rng.uniform(0.9, 1.1, n)
    return pd.DataFrame({
        "item_key": itens,
        "categoria_relevante": ["TI / Informatica"] * n,
        "unidade_orgao_uf_sigla": rng.choice(["SP", "RJ"], n),
        "unit_flag": ["unit_comparable"] * n,
        "quantity": quantidade,
        "unit_price": preco,
    })


def test_engineer_features_creates_log_columns():
    df = engineer_features(make_ml_df())
    assert "log_quantity" in df.columns
    assert "log_unit_price" in df.columns
    assert (df["log_unit_price"] > 0).all()


def test_train_and_evaluate_produces_reasonable_error():
    df = engineer_features(make_ml_df(n=300))
    treino, avaliacao = align_categorical_dtypes(df.iloc[:200], df.iloc[200:])
    modelo = train_lightgbm_model(treino)
    resultado = evaluate_model(avaliacao, modelo)
    assert resultado["pct_cobertura"] == 100.0
    assert resultado["mape_mediana"] < 50  # dado sintetico bem separavel por item
