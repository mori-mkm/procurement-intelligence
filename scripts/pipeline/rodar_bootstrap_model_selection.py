"""
Fase 13.11 - Clustered Paired Bootstrap para selecao de modelos.

Duas comparacoes metodologicamente distintas:

1. Selecao entre modelos supervisionados
   - LightGBM
   - XGBoost
   - CatBoost
   - Ridge

   Usa TODAS as 57.452 observacoes da validacao 2025.

2. Comparacao com baseline de negocio
   - LightGBM vs Median Baseline

   Usa somente as observacoes cobertas pelo baseline.

2026 permanece completamente intocado.
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
    clustered_paired_bootstrap,
)


ARQUIVOS = {
    "LightGBM_v0": (
        DATA_DIR
        / "lightgbm_v0_validation_2025_errors.parquet"
    ),
    "XGBoost_v1": (
        DATA_DIR
        / "xgboost_v1_validation_2025_errors.parquet"
    ),
    "CatBoost_v0": (
        DATA_DIR
        / "catboost_v0_validation_2025_errors.parquet"
    ),
    "Ridge_v0": (
        DATA_DIR
        / "ridge_v0_validation_2025_errors.parquet"
    ),
    "Median_Baseline": (
        DATA_DIR
        / "median_baseline_validation_2025_errors.parquet"
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

        required = {
            "observation_id",
            "item_key",
            "abs_log_error",
        }

        missing = required - set(df.columns)

        if missing:
            raise ValueError(
                f"{modelo} sem colunas obrigatorias: "
                f"{sorted(missing)}"
            )

        if df["observation_id"].duplicated().any():
            raise ValueError(
                f"{modelo} possui observation_id duplicado"
            )

        resultados[modelo] = df

    return resultados


def formatar_conclusao(valor):
    traducoes = {
        "reference_better": "LIGHTGBM MELHOR",
        "challenger_better": "CHALLENGER MELHOR",
        "inconclusive": "INCONCLUSIVO",
    }

    return traducoes.get(
        valor,
        valor,
    )


def main():
    print("=" * 85)
    print("FASE 13.11 - CLUSTERED PAIRED BOOTSTRAP | VALIDACAO 2025")
    print("=" * 85)

    # ---------------------------------------------------------
    # 1. Carregar resultados
    # ---------------------------------------------------------
    print("\n[1/4] Carregando artefatos...")

    resultados = carregar_resultados()

    for modelo, df in resultados.items():
        print(
            f"{modelo:<18}: "
            f"{len(df):>8,} observacoes"
        )

    lightgbm = resultados["LightGBM_v0"]

    # ---------------------------------------------------------
    # 2. Comparacao entre modelos supervisionados
    # ---------------------------------------------------------
    print("\n[2/4] Bootstrap entre modelos supervisionados...")
    print(
        "Amostra: validacao completa 2025 "
        f"({len(lightgbm):,} observacoes)"
    )

    challengers = [
        "XGBoost_v1",
        "CatBoost_v0",
        "Ridge_v0",
    ]

    resultados_bootstrap = []

    for challenger_name in challengers:
        challenger = resultados[challenger_name]

        resultado = clustered_paired_bootstrap(
            reference_errors=lightgbm,
            challenger_errors=challenger,
            reference_name="LightGBM_v0",
            challenger_name=challenger_name,
            cluster_col="item_key",
            n_bootstrap=5000,
            confidence=0.95,
            random_state=42,
        )

        resultado["comparison_scope"] = (
            "full_validation_2025"
        )

        resultados_bootstrap.append(resultado)

    # ---------------------------------------------------------
    # 3. LightGBM vs Median Baseline
    # ---------------------------------------------------------
    print("\n[3/4] Bootstrap contra Median Baseline...")

    median = resultados["Median_Baseline"]

    median_ids = set(
        median["observation_id"].tolist()
    )

    lightgbm_same_sample = (
        lightgbm[
            lightgbm["observation_id"].isin(
                median_ids
            )
        ]
        .copy()
    )

    print(
        f"Amostra coberta pelo baseline: "
        f"{len(median):,} observacoes"
    )

    resultado_baseline = clustered_paired_bootstrap(
        reference_errors=lightgbm_same_sample,
        challenger_errors=median,
        reference_name="LightGBM_v0",
        challenger_name="Median_Baseline",
        cluster_col="item_key",
        n_bootstrap=5000,
        confidence=0.95,
        random_state=42,
    )

    resultado_baseline["comparison_scope"] = (
        "median_same_sample_2025"
    )

    resultados_bootstrap.append(
        resultado_baseline
    )

    # ---------------------------------------------------------
    # 4. Mostrar e salvar resultados
    # ---------------------------------------------------------
    print("\n[4/4] Consolidando resultados...")

    df_resultados = pd.DataFrame(
        resultados_bootstrap
    )

    print("\n" + "=" * 85)
    print("RESULTADOS DO BOOTSTRAP")
    print("=" * 85)

    for _, row in df_resultados.iterrows():

        print("\n" + "-" * 85)

        print(
            f"{row['reference_model']} "
            f"vs {row['challenger_model']}"
        )

        print("-" * 85)

        print(
            f"Escopo:                  "
            f"{row['comparison_scope']}"
        )

        print(
            f"N transacoes:            "
            f"{int(row['n_transacoes']):,}"
        )

        print(
            f"N item_key clusters:     "
            f"{int(row['n_clusters']):,}"
        )

        print(
            f"MAE log LightGBM:        "
            f"{row['reference_mae_log']:.6f}"
        )

        print(
            f"MAE log challenger:      "
            f"{row['challenger_mae_log']:.6f}"
        )

        print(
            f"Delta challenger - LGBM: "
            f"{row['delta_mae_log']:+.6f}"
        )

        print(
            f"Diferenca relativa:      "
            f"{row['relative_difference_pct']:+.2f}%"
        )

        print(
            f"IC 95% delta:            "
            f"[{row['ci_low']:+.6f}, "
            f"{row['ci_high']:+.6f}]"
        )

        print(
            f"Conclusao:               "
            f"{formatar_conclusao(row['conclusion'])}"
        )

    csv_path = (
        DATA_DIR
        / "bootstrap_model_selection_2025.csv"
    )

    json_path = (
        DATA_DIR
        / "bootstrap_model_selection_2025.json"
    )

    df_resultados.to_csv(
        csv_path,
        index=False,
    )

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            resultados_bootstrap,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "=" * 85)
    print("ARQUIVOS SALVOS")
    print("=" * 85)

    print(csv_path)
    print(json_path)

    print("\n" + "=" * 85)
    print("2026 permanece intocado.")
    print("=" * 85)


if __name__ == "__main__":
    main()