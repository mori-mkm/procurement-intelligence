import numpy as np
import pandas as pd
import pytest

from src.analytics.model_selection import (
    build_prediction_errors,
    evaluate_prediction_errors,
    clustered_paired_bootstrap,
)


def test_perfect_prediction_has_zero_error():
    df = pd.DataFrame(
        {
            "item_key": ["notebook", "monitor", "mouse"],
            "unit_price": [100.0, 200.0, 50.0],
        }
    )

    log_pred = np.log(df["unit_price"].values)

    errors = build_prediction_errors(
        df=df,
        log_pred=log_pred,
        model_name="perfect_model",
    )

    metrics = evaluate_prediction_errors(errors)

    assert metrics["mae_log"] == pytest.approx(0.0)
    assert metrics["rmse_log"] == pytest.approx(0.0)
    assert metrics["medape"] == pytest.approx(0.0)
    assert metrics["wape"] == pytest.approx(0.0)


def test_known_and_unseen_items_are_identified():
    df = pd.DataFrame(
        {
            "item_key": [
                "notebook",
                "monitor",
                "produto_novo",
            ],
            "unit_price": [100.0, 200.0, 300.0],
        }
    )

    log_pred = np.log(df["unit_price"].values)

    errors = build_prediction_errors(
        df=df,
        log_pred=log_pred,
        model_name="test_model",
        train_item_keys={"notebook", "monitor"},
    )

    assert errors["is_known_item"].tolist() == [
        True,
        True,
        False,
    ]


def test_known_item_rate_is_computed():
    df = pd.DataFrame(
        {
            "item_key": [
                "a",
                "b",
                "novo",
                "outro_novo",
            ],
            "unit_price": [10.0, 20.0, 30.0, 40.0],
        }
    )

    log_pred = np.log(df["unit_price"].values)

    errors = build_prediction_errors(
        df=df,
        log_pred=log_pred,
        model_name="test_model",
        train_item_keys={"a", "b"},
    )

    metrics = evaluate_prediction_errors(errors)

    assert metrics["known_item_rate"] == pytest.approx(50.0)
    assert metrics["unseen_item_rate"] == pytest.approx(50.0)


def test_length_mismatch_raises_error():
    df = pd.DataFrame(
        {
            "item_key": ["a", "b"],
            "unit_price": [10.0, 20.0],
        }
    )

    log_pred = np.array([1.0])

    with pytest.raises(ValueError):
        build_prediction_errors(
            df=df,
            log_pred=log_pred,
            model_name="test_model",
        )


def test_observation_id_preserves_original_index():
    df = pd.DataFrame(
        {
            "item_key": ["a", "b", "c"],
            "unit_price": [10.0, 20.0, 30.0],
        },
        index=[101, 205, 999],
    )

    log_pred = np.log(df["unit_price"].values)

    errors = build_prediction_errors(
        df=df,
        log_pred=log_pred,
        model_name="test_model",
    )

    assert errors["observation_id"].tolist() == [
        101,
        205,
        999,
    ]


def test_clustered_bootstrap_detects_reference_better():
    reference = pd.DataFrame(
        {
            "observation_id": [1, 2, 3, 4, 5, 6],
            "item_key": [
                "a", "a",
                "b", "b",
                "c", "c",
            ],
            "abs_log_error": [
                1.0, 1.0,
                1.0, 1.0,
                1.0, 1.0,
            ],
        }
    )

    challenger = pd.DataFrame(
        {
            "observation_id": [1, 2, 3, 4, 5, 6],
            "item_key": [
                "a", "a",
                "b", "b",
                "c", "c",
            ],
            "abs_log_error": [
                2.0, 2.0,
                2.0, 2.0,
                2.0, 2.0,
            ],
        }
    )

    result = clustered_paired_bootstrap(
        reference_errors=reference,
        challenger_errors=challenger,
        reference_name="reference",
        challenger_name="challenger",
        n_bootstrap=500,
        random_state=42,
    )

    assert result["delta_mae_log"] == pytest.approx(1.0)
    assert result["ci_low"] > 0
    assert result["ci_high"] > 0
    assert result["conclusion"] == "reference_better"


def test_clustered_bootstrap_identical_models_is_inconclusive():
    reference = pd.DataFrame(
        {
            "observation_id": [1, 2, 3, 4],
            "item_key": [
                "a", "a",
                "b", "b",
            ],
            "abs_log_error": [
                1.0, 2.0,
                3.0, 4.0,
            ],
        }
    )

    challenger = reference.copy()

    result = clustered_paired_bootstrap(
        reference_errors=reference,
        challenger_errors=challenger,
        reference_name="reference",
        challenger_name="challenger",
        n_bootstrap=500,
        random_state=42,
    )

    assert result["delta_mae_log"] == pytest.approx(0.0)
    assert result["ci_low"] == pytest.approx(0.0)
    assert result["ci_high"] == pytest.approx(0.0)
    assert result["conclusion"] == "inconclusive"


def test_clustered_bootstrap_rejects_different_samples():
    reference = pd.DataFrame(
        {
            "observation_id": [1, 2, 3],
            "item_key": ["a", "b", "c"],
            "abs_log_error": [1.0, 1.0, 1.0],
        }
    )

    challenger = pd.DataFrame(
        {
            "observation_id": [1, 2],
            "item_key": ["a", "b"],
            "abs_log_error": [1.0, 1.0],
        }
    )

    with pytest.raises(ValueError):
        clustered_paired_bootstrap(
            reference_errors=reference,
            challenger_errors=challenger,
            reference_name="reference",
            challenger_name="challenger",
            n_bootstrap=100,
        )