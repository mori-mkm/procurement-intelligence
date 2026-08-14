"""
Camada de dados do dashboard.

Centraliza a leitura dos artefatos oficiais produzidos
pelas etapas de validacao, anomaly detection, savings
e model monitoring.

O dashboard deve consumir estes artefatos sem:
- treinar modelos;
- recalibrar thresholds;
- recalcular metricas de validacao;
- reconstruir savings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ARTIFACT_FILES = {
    # Model OOT
    "oot_errors": "lightgbm_final_oot_2026_errors.parquet",
    "oot_metrics": "lightgbm_final_oot_2026_metrics.json",

    # Anomaly Detection
    "anomalies_2026": "anomalies_oot_2026.parquet",
    "anomaly_summary": "anomaly_calibration_2025_2026_summary.json",

    # Savings
    "savings": "savings_dashboard_oot_2026.parquet",
    "savings_summary": "savings_dashboard_oot_2026_summary.json",

    # Stability / Drift
    "stability_overall": "stability_overall_2025_vs_2026.csv",
    "stability_cold_start": "stability_cold_start_2025_vs_2026.csv",
    "stability_category": "stability_category_2025_vs_2026.csv",
    "category_mix_drift": "drift_category_mix_2025_vs_2026.csv",
    "distribution_drift": "drift_distribution_2025_vs_2026.csv",
    "monthly_2026": "stability_monthly_2026.csv",
    "stability_summary": "stability_drift_2026_summary.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as f:
        return json.load(f)


def validate_dashboard_artifacts(
    project_root: Path,
) -> dict[str, Path]:
    """
    Valida se todos os artefatos obrigatorios existem.
    """

    base_dir = (
        Path(project_root)
        / "data"
        / "model_validation"
    )

    paths = {
        key: base_dir / filename
        for key, filename in ARTIFACT_FILES.items()
    }

    missing = [
        path
        for path in paths.values()
        if not path.exists()
    ]

    if missing:
        formatted = "\n".join(
            f"- {path}"
            for path in missing
        )

        raise FileNotFoundError(
            "Artefatos obrigatorios do dashboard "
            "nao encontrados:\n"
            f"{formatted}"
        )

    return paths


def load_dashboard_artifacts(
    project_root: Path,
) -> dict[str, Any]:
    """
    Carrega artefatos oficiais utilizados pelo dashboard.
    """

    paths = validate_dashboard_artifacts(
        project_root
    )

    return {
        # -----------------------------------------------------
        # Model OOT
        # -----------------------------------------------------
        "oot_errors": pd.read_parquet(
            paths["oot_errors"]
        ),

        "oot_metrics": _read_json(
            paths["oot_metrics"]
        ),

        # -----------------------------------------------------
        # Anomaly Detection
        # -----------------------------------------------------
        "anomalies_2026": pd.read_parquet(
            paths["anomalies_2026"]
        ),

        "anomaly_summary": _read_json(
            paths["anomaly_summary"]
        ),

        # -----------------------------------------------------
        # Savings
        # -----------------------------------------------------
        "savings": pd.read_parquet(
            paths["savings"]
        ),

        "savings_summary": _read_json(
            paths["savings_summary"]
        ),

        # -----------------------------------------------------
        # Stability / Drift
        # -----------------------------------------------------
        "stability_overall": pd.read_csv(
            paths["stability_overall"]
        ),

        "stability_cold_start": pd.read_csv(
            paths["stability_cold_start"]
        ),

        "stability_category": pd.read_csv(
            paths["stability_category"]
        ),

        "category_mix_drift": pd.read_csv(
            paths["category_mix_drift"]
        ),

        "distribution_drift": pd.read_csv(
            paths["distribution_drift"]
        ),

        "monthly_2026": pd.read_csv(
            paths["monthly_2026"]
        ),

        "stability_summary": _read_json(
            paths["stability_summary"]
        ),
    }