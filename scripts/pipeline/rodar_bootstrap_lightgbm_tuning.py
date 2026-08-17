"""
Fase 13.12.3 - Comparacao LightGBM v0 vs LightGBM tuned.

Objetivo:
- comparar os dois modelos exatamente nas mesmas observacoes de 2025;
- usar clustered paired bootstrap por item_key;
- verificar se o pequeno ganho observado no tuning e consistente;
- 2026 permanece intocado.

IMPORTANTE:
O tuned foi escolhido usando a propria validacao 2025.
Portanto, mesmo um resultado favoravel deve ser interpretado com cautela.
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
    evaluate_prediction_errors,
)


def carregar(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {caminho}"
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
            f"Colunas obrigatorias ausentes: {sorted(missing)}"
        )

    if df["observation_id"].duplicated().any():
        raise ValueError(
            f"observation_id duplicado em {caminho.name}"
        )

    return df


def main():
    print("=" * 80)
    print("FASE 13.12.3 - LIGHTGBM V0 VS TUNED")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. Carregar artefatos
    # ---------------------------------------------------------
    print("\n[1/4] Carregando resultados...")

    v0_path = (
        DATA_DIR
        / "lightgbm_v0_validation_2025_errors.parquet"
    )

    tuned_path = (
        DATA_DIR
        / "lightgbm_tuned_validation_2025_errors.parquet"
    )

    v0 = carregar(v0_path)
    tuned = carregar(tuned_path)

    print(f"LightGBM v0:     {len(v0):,}")
    print(f"LightGBM tuned:  {len(tuned):,}")

    # ---------------------------------------------------------
    # 2. Integridade da amostra
    # ---------------------------------------------------------
    print("\n[2/4] Validando alinhamento...")

    ids_v0 = set(
        v0["observation_id"]
    )

    ids_tuned = set(
        tuned["observation_id"]
    )

    if ids_v0 != ids_tuned:
        raise ValueError(
            "v0 e tuned nao possuem exatamente os mesmos observation_id"
        )

    check = (
        v0[
            [
                "observation_id",
                "item_key",
            ]
        ]
        .merge(
            tuned[
                [
                    "observation_id",
                    "item_key",
                ]
            ],
            on="observation_id",
            suffixes=("_v0", "_tuned"),
            validate="one_to_one",
        )
    )

    item_v0 = (
        check["item_key_v0"]
        .astype("string")
        .fillna("__NULL__")
    )

    item_tuned = (
        check["item_key_tuned"]
        .astype("string")
        .fillna("__NULL__")
    )

    desalinhados = int(
        (item_v0 != item_tuned).sum()
    )

    print(
        f"Observation IDs:       {len(ids_v0):,}"
    )

    print(
        f"item_key desalinhados: {desalinhados:,}"
    )

    if desalinhados > 0:
        raise ValueError(
            "item_key desalinhado entre v0 e tuned"
        )

    # ---------------------------------------------------------
    # 3. Metricas observadas
    # ---------------------------------------------------------
    print("\n[3/4] Calculando metricas observadas...")

    metrics_v0 = evaluate_prediction_errors(v0)
    metrics_tuned = evaluate_prediction_errors(tuned)

    melhoria_pct = (
        100
        * (
            metrics_v0["mae_log"]
            - metrics_tuned["mae_log"]
        )
        / metrics_v0["mae_log"]
    )

    print("\nLIGHTGBM V0")
    print(
        f"MAE log:   {metrics_v0['mae_log']:.6f}"
    )
    print(
        f"RMSE log:  {metrics_v0['rmse_log']:.6f}"
    )
    print(
        f"MedAPE:    {metrics_v0['medape']:.2f}%"
    )
    print(
        f"WAPE:      {metrics_v0['wape']:.2f}%"
    )

    print("\nLIGHTGBM TUNED")
    print(
        f"MAE log:   {metrics_tuned['mae_log']:.6f}"
    )
    print(
        f"RMSE log:  {metrics_tuned['rmse_log']:.6f}"
    )
    print(
        f"MedAPE:    {metrics_tuned['medape']:.2f}%"
    )
    print(
        f"WAPE:      {metrics_tuned['wape']:.2f}%"
    )

    print(
        f"\nMelhoria observada MAE log: "
        f"{melhoria_pct:+.3f}%"
    )

    # ---------------------------------------------------------
    # 4. Bootstrap
    # ---------------------------------------------------------
    print("\n[4/4] Executando clustered paired bootstrap...")

    resultado = clustered_paired_bootstrap(
        reference_errors=v0,
        challenger_errors=tuned,

        reference_name="LightGBM_v0",
        challenger_name="LightGBM_tuned",

        cluster_col="item_key",

        n_bootstrap=5000,
        confidence=0.95,
        random_state=42,
    )

    print("\n" + "=" * 80)
    print("RESULTADO DO BOOTSTRAP")
    print("=" * 80)

    print(
        f"N transacoes:          "
        f"{resultado['n_transacoes']:,}"
    )

    print(
        f"N item_key clusters:   "
        f"{resultado['n_clusters']:,}"
    )

    print(
        f"MAE log v0:            "
        f"{resultado['reference_mae_log']:.6f}"
    )

    print(
        f"MAE log tuned:         "
        f"{resultado['challenger_mae_log']:.6f}"
    )

    print(
        f"Delta tuned - v0:      "
        f"{resultado['delta_mae_log']:+.6f}"
    )

    print(
        f"Diferenca relativa:    "
        f"{resultado['relative_difference_pct']:+.3f}%"
    )

    print(
        f"IC 95% delta:          "
        f"[{resultado['ci_low']:+.6f}, "
        f"{resultado['ci_high']:+.6f}]"
    )

    print(
        f"Conclusao estatistica: "
        f"{resultado['conclusion']}"
    )

    # ---------------------------------------------------------
    # Persistir
    # ---------------------------------------------------------
    output_path = (
        DATA_DIR
        / "bootstrap_lightgbm_v0_vs_tuned_2025.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            resultado,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\nARQUIVO SALVO")
    print(output_path)

    print("\n" + "=" * 80)
    print("2026 permanece intocado.")
    print("=" * 80)


if __name__ == "__main__":
    main()