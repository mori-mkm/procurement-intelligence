import numpy as np
import pandas as pd

from src.analytics.anomaly_detection import (
    compute_residuals,
    flag_price_anomalies,
    summarize_anomalies,
    calibrate_anomaly_threshold,
    flag_price_anomalies_frozen,
)

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


def test_calibrate_threshold_uses_only_known_items():
    errors = pd.DataFrame(
        {
            "abs_log_error": [
                0.10,
                0.20,
                0.30,
                100.0,
            ],
            "is_known_item": [
                True,
                True,
                True,
                False,
            ],
        }
    )

    threshold = calibrate_anomaly_threshold(
        errors,
        percentil=100,
        known_only=True,
    )

    assert threshold == 0.30


def test_frozen_threshold_excludes_unseen_items():
    errors = pd.DataFrame(
        {
            "log_unit_price_real": [
                1.0,
                3.0,
            ],
            "log_unit_price_pred": [
                0.0,
                0.0,
            ],
            "unit_price": [
                np.exp(1.0),
                np.exp(3.0),
            ],
            "unit_price_pred": [
                1.0,
                1.0,
            ],
            "abs_log_error": [
                1.0,
                3.0,
            ],
            "is_known_item": [
                True,
                False,
            ],
        }
    )

    result = flag_price_anomalies_frozen(
        errors,
        threshold=0.5,
        known_only=True,
    )

    assert result["is_price_anomaly"].iloc[0]
    assert not result["is_price_anomaly"].iloc[1]

    assert (
        result["anomaly_direction"].iloc[0]
        == "acima_do_esperado"
    )

    assert (
        result["anomaly_direction"].iloc[1]
        == "nao_avaliavel"
    )


def test_frozen_threshold_does_not_recalculate_from_dataset():
    errors = pd.DataFrame(
        {
            "log_unit_price_real": [
                0.1,
                0.2,
                10.0,
            ],
            "log_unit_price_pred": [
                0.0,
                0.0,
                0.0,
            ],
            "unit_price": [
                np.exp(0.1),
                np.exp(0.2),
                np.exp(10.0),
            ],
            "unit_price_pred": [
                1.0,
                1.0,
                1.0,
            ],
            "abs_log_error": [
                0.1,
                0.2,
                10.0,
            ],
            "is_known_item": [
                True,
                True,
                True,
            ],
        }
    )

    result = flag_price_anomalies_frozen(
        errors,
        threshold=0.15,
    )

    assert (
        result["is_price_anomaly"].tolist()
        == [False, True, True]
    )

    assert (
        result["anomaly_threshold_abs_log"]
        == 0.15
    ).all()