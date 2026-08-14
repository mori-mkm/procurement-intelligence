import numpy as np
import pandas as pd

from src.analytics.anomaly_detection import compute_residuals, flag_price_anomalies, summarize_anomalies


class FakeModel:
    """Modelo falso: sempre preve log(100) -- simplifica teste de residuo."""
    def predict(self, X):
        return np.full(len(X), np.log(100.0))


def make_df():
    return pd.DataFrame({
        "item_key": ["x"] * 10,
        "categoria_relevante": ["TI / Informatica"] * 10,
        "unidade_orgao_uf_sigla": ["SP"] * 10,
        "unit_flag": ["unit_comparable"] * 10,
        "log_quantity": [1.0] * 10,
        "unit_price": [100.0] * 9 + [10000.0],  # 1 outlier evidente
        "total_price": [100.0] * 9 + [10000.0],
    })


def test_compute_residuals_and_flag_extreme():
    df = compute_residuals(make_df(), FakeModel())
    df = flag_price_anomalies(df, percentil=90)
    assert df["is_price_anomaly"].iloc[-1] == True
    assert df["anomaly_direction"].iloc[-1] == "acima_do_esperado"


def test_summarize_anomalies_counts_correctly():
    df = compute_residuals(make_df(), FakeModel())
    df = flag_price_anomalies(df, percentil=90)
    resumo = summarize_anomalies(df)
    assert resumo["n_anomalias"] == 1
    assert resumo["n_acima_do_esperado"] == 1


def test_flag_price_anomalies_excludes_null_item_key():
    df = make_df()
    df.loc[0, "item_key"] = None
    df.loc[0, "unit_price"] = 999999.0  # seria a maior anomalia se nao fosse excluida
    df = compute_residuals(df, FakeModel())
    df = flag_price_anomalies(df, percentil=90)
    assert df["is_price_anomaly"].iloc[0] == False
    assert df["anomaly_direction"].iloc[0] == "nao_avaliavel"