"""
Fase 13.10 - Comparacao same-sample dos candidatos.

Objetivo:
- usar exclusivamente validacao 2025;
- utilizar como amostra comum as observacoes cobertas pelo Median Baseline;
- comparar Median, Ridge, LightGBM, CatBoost e XGBoost
  exatamente nas mesmas transacoes;
- verificar integridade dos observation_id antes da comparacao;
- nao utilizar 2026.
"""

import json
import sys
from pathlib import Path

import pandas as pd


def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()

    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai

    raise RuntimeError("Nao encontrei a raiz do projeto")


RAIZ = achar_raiz_projeto(Path(__file__))
sys.path.insert(0, str(RAIZ))

DATA_DIR = RAIZ / "data" / "model_validation"


from src.analytics.model_selection import (
    evaluate_prediction_errors,
)


ARQUIVOS = {
    "Median_Baseline": (
        DATA_DIR
        / "median_baseline_validation_2025_errors.parquet"
    ),
    "Ridge_v0": (
        DATA_DIR
        / "ridge_v0_validation_2025_errors.parquet"
    ),
    "LightGBM_v0": (
        DATA_DIR
        / "lightgbm_v0_validation_2025_errors.parquet"
    ),
    "CatBoost_v0": (
        DATA_DIR
        / "catboost_v0_validation_2025_errors.parquet"
    ),
    "XGBoost_v1": (
        DATA_DIR
        / "xgboost_v1_validation_2025_errors.parquet"
    ),
}


def carregar_resultados():
    resultados = {}

    for modelo, caminho in ARQUIVOS.items():
        if not caminho.exists():
            raise FileNotFoundError(
                f"Arquivo ausente para {modelo}: {caminho}"
            )

        df = pd.read_parquet(caminho)

        if "observation_id" not in df.columns:
            raise ValueError(
                f"{modelo} nao possui observation_id"
            )

        if df["observation_id"].duplicated().any():
            raise ValueError(
                f"{modelo} possui observation_id duplicado"
            )

        resultados[modelo] = df

    return resultados


def main():
    print("=" * 80)
    print("FASE 13.10 - COMPARACAO SAME-SAMPLE | VALIDACAO 2025")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. Carregar artefatos
    # ---------------------------------------------------------
    print("\n[1/5] Carregando resultados...")

    resultados = carregar_resultados()

    for modelo, df in resultados.items():
        print(
            f"{modelo:<18}: "
            f"{len(df):>8,} observacoes"
        )

    # ---------------------------------------------------------
    # 2. Definir a amostra comum
    # ---------------------------------------------------------
    print("\n[2/5] Definindo same-sample...")

    baseline = resultados["Median_Baseline"]

    ids_comuns = set(
        baseline["observation_id"].tolist()
    )

    for modelo, df in resultados.items():
        ids_modelo = set(
            df["observation_id"].tolist()
        )

        faltantes = ids_comuns - ids_modelo

        if faltantes:
            raise ValueError(
                f"{modelo} nao contem "
                f"{len(faltantes):,} observation_id "
                "presentes no baseline"
            )

    print(
        f"Observation IDs da amostra comum: "
        f"{len(ids_comuns):,}"
    )

    # ---------------------------------------------------------
    # 3. Filtrar todos para exatamente os mesmos IDs
    # ---------------------------------------------------------
    print("\n[3/5] Alinhando modelos...")

    aligned = {}

    ordem_ids = (
        baseline["observation_id"]
        .tolist()
    )

    for modelo, df in resultados.items():
        temp = (
            df[
                df["observation_id"].isin(ids_comuns)
            ]
            .set_index("observation_id")
            .loc[ordem_ids]
            .reset_index()
        )

        if len(temp) != len(baseline):
            raise ValueError(
                f"Amostra desalinhada para {modelo}"
            )

        aligned[modelo] = temp

    # Verifica se todos estao comparando o mesmo preco real
    referencia = (
        aligned["Median_Baseline"]
        .set_index("observation_id")["unit_price"]
    )

    for modelo, df in aligned.items():
        atual = (
            df
            .set_index("observation_id")["unit_price"]
        )

        if not referencia.equals(atual):
            raise ValueError(
                f"unit_price desalinhado em {modelo}"
            )

    print("Integridade same-sample: OK")

    # ---------------------------------------------------------
    # 4. Calcular metricas
    # ---------------------------------------------------------
    print("\n[4/5] Calculando metricas...")

    linhas = []

    for modelo, df in aligned.items():
        metrics = evaluate_prediction_errors(df)

        linhas.append(
            {
                "modelo": modelo,
                "n": metrics["n_transacoes"],
                "mae_log": metrics["mae_log"],
                "rmse_log": metrics["rmse_log"],
                "medape": metrics["medape"],
                "wape": metrics["wape"],
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
            }
        )

    ranking = (
        pd.DataFrame(linhas)
        .sort_values("mae_log")
        .reset_index(drop=True)
    )

    baseline_mae_log = float(
        ranking.loc[
            ranking["modelo"] == "Median_Baseline",
            "mae_log",
        ].iloc[0]
    )

    ranking["melhoria_vs_baseline_pct"] = (
        100
        * (
            baseline_mae_log
            - ranking["mae_log"]
        )
        / baseline_mae_log
    )

    print("\n" + "=" * 80)
    print("RESULTADO SAME-SAMPLE")
    print("=" * 80)

    tabela_print = ranking[
        [
            "modelo",
            "n",
            "mae_log",
            "rmse_log",
            "medape",
            "wape",
            "melhoria_vs_baseline_pct",
        ]
    ].copy()

    print(
        tabela_print.to_string(
            index=False,
            formatters={
                "mae_log": "{:.6f}".format,
                "rmse_log": "{:.6f}".format,
                "medape": "{:.2f}%".format,
                "wape": "{:.2f}%".format,
                "melhoria_vs_baseline_pct":
                    "{:+.2f}%".format,
            },
        )
    )

    # ---------------------------------------------------------
    # 5. Persistir
    # ---------------------------------------------------------
    print("\n[5/5] Salvando comparacao...")

    csv_path = (
        DATA_DIR
        / "model_comparison_same_sample_2025.csv"
    )

    json_path = (
        DATA_DIR
        / "model_comparison_same_sample_2025.json"
    )

    ranking.to_csv(
        csv_path,
        index=False,
    )

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            ranking.to_dict(orient="records"),
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\nARQUIVOS SALVOS")
    print(csv_path)
    print(json_path)

    print("\n" + "=" * 80)
    print("2026 permanece intocado.")
    print("=" * 80)


if __name__ == "__main__":
    main()