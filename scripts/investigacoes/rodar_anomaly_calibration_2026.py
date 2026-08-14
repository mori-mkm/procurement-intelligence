"""
Fase 13.14.2 - Calibracao temporal do Anomaly Detection.

Protocolo:

2025:
    residuals do LightGBM v0
    ↓
    somente itens known
    ↓
    calibrar P95 do abs_log_error
    ↓
    congelar threshold

2026:
    residuals do modelo final OOT
    ↓
    aplicar exatamente o mesmo threshold
    ↓
    nenhuma recalibracao usando 2026
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()

    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai

    raise RuntimeError("Nao encontrei a raiz do projeto")


RAIZ = achar_raiz_projeto(Path(__file__))
sys.path.insert(0, str(RAIZ))

OUTPUT_DIR = RAIZ / "data" / "model_validation"


from src.analytics.anomaly_detection import (
    calibrate_anomaly_threshold,
    flag_price_anomalies_frozen,
)


PERCENTIL = 95.0


def carregar_erros(nome: str) -> pd.DataFrame:
    caminho = OUTPUT_DIR / nome

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {caminho}"
        )

    df = pd.read_parquet(caminho)

    if "observation_id" not in df.columns:
        raise ValueError(
            f"{nome} nao possui observation_id"
        )

    return df


def resumir_anomalias(
    df: pd.DataFrame,
    periodo: str,
) -> dict:

    avaliavel = df[
        df["is_known_item"]
        .fillna(False)
        .astype(bool)
    ].copy()

    anomalias = avaliavel[
        avaliavel["is_price_anomaly"]
    ].copy()

    acima = anomalias[
        anomalias["anomaly_direction"]
        == "acima_do_esperado"
    ]

    abaixo = anomalias[
        anomalias["anomaly_direction"]
        == "abaixo_do_esperado"
    ]

    n_total = len(df)
    n_avaliavel = len(avaliavel)
    n_anomalias = len(anomalias)

    return {
        "periodo": periodo,

        "n_total": int(n_total),

        "n_avaliavel_known": int(
            n_avaliavel
        ),

        "coverage_pct": float(
            100 * n_avaliavel / n_total
            if n_total > 0
            else 0
        ),

        "n_anomalias": int(
            n_anomalias
        ),

        "anomaly_rate_pct": float(
            100 * n_anomalias / n_avaliavel
            if n_avaliavel > 0
            else 0
        ),

        "n_acima_esperado": int(
            len(acima)
        ),

        "n_abaixo_esperado": int(
            len(abaixo)
        ),

        "pct_acima_entre_anomalias": float(
            100 * len(acima) / n_anomalias
            if n_anomalias > 0
            else 0
        ),

        "pct_abaixo_entre_anomalias": float(
            100 * len(abaixo) / n_anomalias
            if n_anomalias > 0
            else 0
        ),

        "abs_log_error_median": float(
            avaliavel["abs_log_error"].median()
        ),

        "abs_log_error_p95": float(
            avaliavel["abs_log_error"]
            .quantile(0.95)
        ),
    }


def main():
    print("=" * 85)
    print("FASE 13.14.2 - ANOMALY THRESHOLD CALIBRATION")
    print("=" * 85)

    # ---------------------------------------------------------
    # 1. Carregar erros congelados
    # ---------------------------------------------------------
    print("\n[1/5] Carregando residuals...")

    errors_2025 = carregar_erros(
        "lightgbm_v0_validation_2025_errors.parquet"
    )

    errors_2026 = carregar_erros(
        "lightgbm_final_oot_2026_errors.parquet"
    )

    print(
        f"Validacao 2025: {len(errors_2025):,}"
    )

    print(
        f"Teste OOT 2026: {len(errors_2026):,}"
    )

    # ---------------------------------------------------------
    # 2. Calibrar threshold SOMENTE em 2025 known
    # ---------------------------------------------------------
    print("\n[2/5] Calibrando threshold em 2025...")

    threshold = calibrate_anomaly_threshold(
        errors=errors_2025,
        percentil=PERCENTIL,
        known_only=True,
    )

    multiplicative_factor = float(
        np.exp(threshold)
    )

    print(
        f"Percentil calibracao: P{PERCENTIL:.0f}"
    )

    print(
        f"Threshold abs_log_error: "
        f"{threshold:.6f}"
    )

    print(
        f"Fator multiplicativo aproximado: "
        f"{multiplicative_factor:.2f}x"
    )

    print(
        "\nThreshold agora esta CONGELADO."
    )

    # ---------------------------------------------------------
    # 3. Aplicar em 2025
    # ---------------------------------------------------------
    print("\n[3/5] Aplicando threshold na calibracao 2025...")

    anomalies_2025 = flag_price_anomalies_frozen(
        errors=errors_2025,
        threshold=threshold,
        known_only=True,
    )

    resumo_2025 = resumir_anomalias(
        anomalies_2025,
        "2025_validation",
    )

    # ---------------------------------------------------------
    # 4. Aplicar MESMO threshold em 2026
    # ---------------------------------------------------------
    print("\n[4/5] Aplicando threshold congelado em 2026...")

    anomalies_2026 = flag_price_anomalies_frozen(
        errors=errors_2026,
        threshold=threshold,
        known_only=True,
    )

    resumo_2026 = resumir_anomalias(
        anomalies_2026,
        "2026_oot",
    )

    # ---------------------------------------------------------
    # Resultado
    # ---------------------------------------------------------
    print("\n" + "=" * 85)
    print("RESULTADO — THRESHOLD CONGELADO")
    print("=" * 85)

    print(
        f"\nThreshold P95 2025: "
        f"{threshold:.6f}"
    )

    print(
        f"Equivalente multiplicativo: "
        f"{multiplicative_factor:.2f}x"
    )

    for resumo in [
        resumo_2025,
        resumo_2026,
    ]:

        print("\n" + "-" * 85)

        print(
            resumo["periodo"]
        )

        print("-" * 85)

        print(
            f"N total:                  "
            f"{resumo['n_total']:,}"
        )

        print(
            f"N avaliavel (known):       "
            f"{resumo['n_avaliavel_known']:,}"
        )

        print(
            f"Cobertura:                 "
            f"{resumo['coverage_pct']:.2f}%"
        )

        print(
            f"N anomalias:               "
            f"{resumo['n_anomalias']:,}"
        )

        print(
            f"Taxa anomalias:            "
            f"{resumo['anomaly_rate_pct']:.2f}%"
        )

        print(
            f"Acima do esperado:         "
            f"{resumo['n_acima_esperado']:,}"
        )

        print(
            f"Abaixo do esperado:        "
            f"{resumo['n_abaixo_esperado']:,}"
        )

        print(
            f"% acima entre anomalias:   "
            f"{resumo['pct_acima_entre_anomalias']:.2f}%"
        )

        print(
            f"% abaixo entre anomalias:  "
            f"{resumo['pct_abaixo_entre_anomalias']:.2f}%"
        )

    # ---------------------------------------------------------
    # 5. Persistir
    # ---------------------------------------------------------
    print("\n[5/5] Salvando resultados...")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    threshold_path = (
        OUTPUT_DIR
        / "anomaly_threshold_calibrated_2025.json"
    )

    anomalies_2025_path = (
        OUTPUT_DIR
        / "anomalies_validation_2025.parquet"
    )

    anomalies_2026_path = (
        OUTPUT_DIR
        / "anomalies_oot_2026.parquet"
    )

    summary_path = (
        OUTPUT_DIR
        / "anomaly_calibration_2025_2026_summary.json"
    )

    threshold_payload = {
        "calibration_period": 2025,
        "percentile": PERCENTIL,
        "known_only": True,
        "threshold_abs_log_error": threshold,
        "multiplicative_factor": multiplicative_factor,
        "test_period": 2026,
        "recalibrated_on_test": False,
    }

    with threshold_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            threshold_payload,
            f,
            indent=2,
            ensure_ascii=False,
        )

    anomalies_2025.to_parquet(
        anomalies_2025_path,
        index=False,
    )

    anomalies_2026.to_parquet(
        anomalies_2026_path,
        index=False,
    )

    summary = {
        "threshold": threshold_payload,
        "validation_2025": resumo_2025,
        "oot_2026": resumo_2026,
    }

    with summary_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\nARQUIVOS SALVOS")

    print(threshold_path)
    print(anomalies_2025_path)
    print(anomalies_2026_path)
    print(summary_path)

    print("\n" + "=" * 85)
    print(
        "FIM — 2026 NAO FOI UTILIZADO PARA CALIBRAR O THRESHOLD."
    )
    print("=" * 85)


if __name__ == "__main__":
    main()