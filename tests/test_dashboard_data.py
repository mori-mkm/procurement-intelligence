import json

import pandas as pd
import pytest

from src.analytics.dashboard_data import (
    ARTIFACT_FILES,
    load_dashboard_artifacts,
    validate_dashboard_artifacts,
)


def _criar_artefatos_fake(tmp_path):
    base = (
        tmp_path
        / "data"
        / "model_validation"
    )

    base.mkdir(
        parents=True
    )

    parquet_files = {
        "oot_errors",
        "anomalies_2026",
        "savings",
        "spend_by_category",
        "hhi_by_category",
    }

    json_files = {
        "oot_metrics",
        "anomaly_summary",
        "savings_summary",
        "stability_summary",
    }

    for key, filename in ARTIFACT_FILES.items():
        path = base / filename

        if key in parquet_files:
            pd.DataFrame(
                {
                    "value": [1]
                }
            ).to_parquet(
                path,
                index=False,
            )

        elif key in json_files:
            with path.open(
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    {"value": 1},
                    f,
                )

        else:
            pd.DataFrame(
                {
                    "value": [1]
                }
            ).to_csv(
                path,
                index=False,
            )

    return base


def test_validate_dashboard_artifacts_detects_missing(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
        match="Artefatos obrigatorios",
    ):
        validate_dashboard_artifacts(
            tmp_path
        )


def test_load_dashboard_artifacts(
    tmp_path,
):
    _criar_artefatos_fake(
        tmp_path
    )

    result = load_dashboard_artifacts(
        tmp_path
    )

    assert set(result) == set(
        ARTIFACT_FILES
    )

    assert len(
        result["oot_errors"]
    ) == 1

    assert len(
        result["savings"]
    ) == 1

    assert (
        result["oot_metrics"]["value"]
        == 1
    )

    assert (
        result["stability_summary"]["value"]
        == 1
    )