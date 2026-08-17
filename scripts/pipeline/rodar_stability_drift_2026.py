"""
Fase 13.13.2 - Stability & Drift Analysis.

Objetivos:
- comparar estabilidade de performance entre validacao 2025 e OOT 2026;
- analisar cold start;
- analisar performance por categoria;
- analisar performance mensal em 2026;
- medir mudanca de mix de categorias;
- comparar distribuicoes de preco e quantidade.

IMPORTANTE:
Os modelos comparados nao possuem exatamente o mesmo treino:

2025:
    LightGBM treinado em 2024.

2026:
    LightGBM final treinado em 2024 + 2025.

Portanto, variacoes de performance sao tratadas como estabilidade temporal,
nao como estimativa causal pura de model drift.
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


from src.transformation.gold import load_gold_layer
from src.analytics.price_baseline import (
    prepare_baseline_dataset,
    split_temporal,
)
from src.analytics.price_ml import (
    engineer_features,
)
from src.analytics.model_selection import (
    evaluate_prediction_errors,
)


def carregar_erros(nome_arquivo: str) -> pd.DataFrame:
    caminho = OUTPUT_DIR / nome_arquivo

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {caminho}"
        )

    df = pd.read_parquet(caminho)

    if "observation_id" not in df.columns:
        raise ValueError(
            f"{nome_arquivo} nao possui observation_id"
        )

    if df["observation_id"].duplicated().any():
        raise ValueError(
            f"{nome_arquivo} possui observation_id duplicado"
        )

    return df


def adicionar_metadados(
    errors: pd.DataFrame,
    original: pd.DataFrame,
) -> pd.DataFrame:
    """
    Reanexa metadados originais usando observation_id.
    """

    metadata_cols = [
        "categoria_relevante",
        "date_key",
        "quantity",
        "log_quantity",
        "log_unit_price",
    ]

    faltantes = (
        set(metadata_cols)
        - set(original.columns)
    )

    if faltantes:
        raise ValueError(
            "Colunas ausentes no dataset original: "
            f"{sorted(faltantes)}"
        )

    metadata = (
        original[metadata_cols]
        .copy()
    )

    metadata["observation_id"] = metadata.index

    enriched = errors.merge(
        metadata,
        on="observation_id",
        how="left",
        validate="one_to_one",
    )

    if len(enriched) != len(errors):
        raise ValueError(
            "Merge de metadados alterou numero de linhas"
        )

    if enriched["date_key"].isna().any():
        raise ValueError(
            "Existem observation_id sem correspondencia no dataset original"
        )

    enriched["data"] = pd.to_datetime(
        enriched["date_key"]
        .astype("Int64")
        .astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    if enriched["data"].isna().any():
        raise ValueError(
            "Falha ao converter date_key para data"
        )

    enriched["mes"] = (
        enriched["data"]
        .dt.to_period("M")
        .astype(str)
    )

    return enriched


def metricas_por_grupo(
    df: pd.DataFrame,
    coluna: str,
) -> pd.DataFrame:

    linhas = []

    for grupo, temp in df.groupby(
        coluna,
        dropna=False,
        sort=True,
    ):
        metrics = evaluate_prediction_errors(
            temp
        )

        linha = {
            coluna: str(grupo),
            "n": int(metrics["n_transacoes"]),
            "mae_log": float(metrics["mae_log"]),
            "rmse_log": float(metrics["rmse_log"]),
            "medape": float(metrics["medape"]),
            "wape": float(metrics["wape"]),
            "mae": float(metrics["mae"]),
            "rmse": float(metrics["rmse"]),
        }

        if "known_item_rate" in metrics:
            linha["known_item_rate"] = float(
                metrics["known_item_rate"]
            )
            linha["unseen_item_rate"] = float(
                metrics["unseen_item_rate"]
            )

        linhas.append(linha)

    return pd.DataFrame(linhas)


def resumo_distribuicao(
    df: pd.DataFrame,
    periodo: str,
) -> dict:

    return {
        "periodo": periodo,
        "n": int(len(df)),

        "unit_price_mediana": float(
            df["unit_price"].median()
        ),

        "unit_price_p25": float(
            df["unit_price"].quantile(0.25)
        ),

        "unit_price_p75": float(
            df["unit_price"].quantile(0.75)
        ),

        "unit_price_p90": float(
            df["unit_price"].quantile(0.90)
        ),

        "log_unit_price_media": float(
            df["log_unit_price"].mean()
        ),

        "log_unit_price_mediana": float(
            df["log_unit_price"].median()
        ),

        "quantity_mediana": float(
            df["quantity"].median()
        ),

        "log_quantity_media": float(
            df["log_quantity"].mean()
        ),
    }


def main():
    print("=" * 90)
    print("FASE 13.13.2 - STABILITY & DRIFT ANALYSIS")
    print("=" * 90)

    # ---------------------------------------------------------
    # 1. Carregar populacao
    # ---------------------------------------------------------
    print("\n[1/7] Carregando dataset oficial...")

    gold = load_gold_layer()
    fact = gold["fact_purchase"]

    df = prepare_baseline_dataset(fact)
    df = engineer_features(df)

    splits = split_temporal(df)

    validacao_2025 = splits["validacao"].copy()
    teste_2026 = splits["teste"].copy()

    print(
        f"Validacao 2025: {len(validacao_2025):,}"
    )

    print(
        f"Teste 2026:     {len(teste_2026):,}"
    )

    # ---------------------------------------------------------
    # 2. Carregar erros
    # ---------------------------------------------------------
    print("\n[2/7] Carregando resultados dos modelos...")

    errors_2025 = carregar_erros(
        "lightgbm_v0_validation_2025_errors.parquet"
    )

    errors_2026 = carregar_erros(
        "lightgbm_final_oot_2026_errors.parquet"
    )

    print(
        f"Erros 2025: {len(errors_2025):,}"
    )

    print(
        f"Erros 2026: {len(errors_2026):,}"
    )

    # ---------------------------------------------------------
    # 3. Reanexar metadados
    # ---------------------------------------------------------
    print("\n[3/7] Reanexando metadados...")

    errors_2025 = adicionar_metadados(
        errors_2025,
        validacao_2025,
    )

    errors_2026 = adicionar_metadados(
        errors_2026,
        teste_2026,
    )

    print("Integridade dos joins: OK")

    # ---------------------------------------------------------
    # 4. Estabilidade global
    # ---------------------------------------------------------
    print("\n[4/7] Avaliando estabilidade global...")

    metrics_2025 = evaluate_prediction_errors(
        errors_2025
    )

    metrics_2026 = evaluate_prediction_errors(
        errors_2026
    )

    metricas_comparar = [
        "mae_log",
        "rmse_log",
        "medape",
        "wape",
        "mae",
        "rmse",
        "known_item_rate",
        "unseen_item_rate",
    ]

    linhas_overall = []

    for metrica in metricas_comparar:

        valor_2025 = metrics_2025.get(
            metrica,
            np.nan,
        )

        valor_2026 = metrics_2026.get(
            metrica,
            np.nan,
        )

        delta = (
            valor_2026
            - valor_2025
        )

        delta_pct = (
            100
            * delta
            / valor_2025
            if valor_2025 not in [0, None]
            and not pd.isna(valor_2025)
            else np.nan
        )

        linhas_overall.append(
            {
                "metrica": metrica,
                "valor_2025": valor_2025,
                "valor_2026": valor_2026,
                "delta": delta,
                "delta_pct": delta_pct,
            }
        )

    overall = pd.DataFrame(
        linhas_overall
    )

    print("\n" + "=" * 90)
    print("ESTABILIDADE GLOBAL")
    print("=" * 90)

    print(
        overall.to_string(
            index=False,
            formatters={
                "valor_2025":
                    "{:.6f}".format,
                "valor_2026":
                    "{:.6f}".format,
                "delta":
                    "{:+.6f}".format,
                "delta_pct":
                    "{:+.2f}%".format,
            },
        )
    )

    # ---------------------------------------------------------
    # Cold start detalhado
    # ---------------------------------------------------------
    print("\n" + "=" * 90)
    print("COLD START")
    print("=" * 90)

    cold_start_rows = []

    for ano, temp in [
        ("2025", errors_2025),
        ("2026", errors_2026),
    ]:

        for status, subset in [
            (
                "known",
                temp[temp["is_known_item"]],
            ),
            (
                "unseen",
                temp[~temp["is_known_item"]],
            ),
        ]:

            metrics = evaluate_prediction_errors(
                subset
            )

            cold_start_rows.append(
                {
                    "ano": ano,
                    "status": status,
                    "n": int(
                        metrics["n_transacoes"]
                    ),
                    "mae_log": float(
                        metrics["mae_log"]
                    ),
                    "rmse_log": float(
                        metrics["rmse_log"]
                    ),
                    "medape": float(
                        metrics["medape"]
                    ),
                    "wape": float(
                        metrics["wape"]
                    ),
                }
            )

    cold_start = pd.DataFrame(
        cold_start_rows
    )

    print(
        cold_start.to_string(
            index=False,
            formatters={
                "mae_log":
                    "{:.6f}".format,
                "rmse_log":
                    "{:.6f}".format,
                "medape":
                    "{:.2f}%".format,
                "wape":
                    "{:.2f}%".format,
            },
        )
    )

    # ---------------------------------------------------------
    # 5. Categoria
    # ---------------------------------------------------------
    print("\n[5/7] Analisando categorias...")

    categoria_2025 = metricas_por_grupo(
        errors_2025,
        "categoria_relevante",
    )

    categoria_2026 = metricas_por_grupo(
        errors_2026,
        "categoria_relevante",
    )

    categoria_comparacao = categoria_2025.merge(
        categoria_2026,
        on="categoria_relevante",
        how="outer",
        suffixes=("_2025", "_2026"),
    )

    categoria_comparacao[
        "delta_mae_log"
    ] = (
        categoria_comparacao["mae_log_2026"]
        - categoria_comparacao["mae_log_2025"]
    )

    categoria_comparacao[
        "delta_mae_log_pct"
    ] = (
        100
        * categoria_comparacao["delta_mae_log"]
        / categoria_comparacao["mae_log_2025"]
    )

    print("\n" + "=" * 90)
    print("PERFORMANCE POR CATEGORIA")
    print("=" * 90)

    print(
        categoria_comparacao[
            [
                "categoria_relevante",
                "n_2025",
                "n_2026",
                "mae_log_2025",
                "mae_log_2026",
                "delta_mae_log_pct",
                "unseen_item_rate_2025",
                "unseen_item_rate_2026",
            ]
        ]
        .sort_values(
            "mae_log_2026",
            ascending=False,
        )
        .to_string(
            index=False,
            formatters={
                "mae_log_2025":
                    "{:.6f}".format,
                "mae_log_2026":
                    "{:.6f}".format,
                "delta_mae_log_pct":
                    "{:+.2f}%".format,
                "unseen_item_rate_2025":
                    "{:.2f}%".format,
                "unseen_item_rate_2026":
                    "{:.2f}%".format,
            },
        )
    )

    # ---------------------------------------------------------
    # 6. Drift de mix
    # ---------------------------------------------------------
    print("\n[6/7] Analisando drift de mix...")

    mix_2025 = (
        validacao_2025["categoria_relevante"]
        .value_counts(
            normalize=True,
            dropna=False,
        )
    )

    mix_2026 = (
        teste_2026["categoria_relevante"]
        .value_counts(
            normalize=True,
            dropna=False,
        )
    )

    categorias = (
        mix_2025.index
        .union(mix_2026.index)
    )

    mix = pd.DataFrame(
        index=categorias
    )

    mix["share_2025_pct"] = (
        mix_2025.reindex(
            categorias,
            fill_value=0,
        )
        * 100
    )

    mix["share_2026_pct"] = (
        mix_2026.reindex(
            categorias,
            fill_value=0,
        )
        * 100
    )

    mix["delta_pp"] = (
        mix["share_2026_pct"]
        - mix["share_2025_pct"]
    )

    mix["abs_delta_pp"] = (
        mix["delta_pp"].abs()
    )

    mix = (
        mix
        .reset_index()
        .rename(
            columns={
                "index":
                    "categoria_relevante"
            }
        )
    )

    # Total Variation Distance:
    # percentual da massa de probabilidade que precisaria
    # mudar de categoria para transformar um mix no outro.
    tvd_pct = float(
        0.5
        * mix["abs_delta_pp"].sum()
    )

    print("\n" + "=" * 90)
    print("MUDANCA DE MIX DE CATEGORIAS")
    print("=" * 90)

    mix_print = (
        mix
        .sort_values(
            "abs_delta_pp",
            ascending=False,
        )
        [
            [
                "categoria_relevante",
                "share_2025_pct",
                "share_2026_pct",
                "delta_pp",
            ]
        ]
    )

    print(
        mix_print.to_string(
            index=False,
            formatters={
                "share_2025_pct":
                    "{:.2f}%".format,
                "share_2026_pct":
                    "{:.2f}%".format,
                "delta_pp":
                    "{:+.2f} p.p.".format,
            },
        )
    )

    print(
        f"\nTotal Variation Distance: "
        f"{tvd_pct:.2f}%"
    )

    # ---------------------------------------------------------
    # Distribuicoes
    # ---------------------------------------------------------
    dist_2025 = resumo_distribuicao(
        validacao_2025,
        "2025",
    )

    dist_2026 = resumo_distribuicao(
        teste_2026,
        "2026",
    )

    distribuicoes = pd.DataFrame(
        [
            dist_2025,
            dist_2026,
        ]
    )

    print("\n" + "=" * 90)
    print("DISTRIBUICAO DE PRECO E QUANTIDADE")
    print("=" * 90)

    print(
        distribuicoes.to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # 7. Performance mensal 2026
    # ---------------------------------------------------------
    print("\n[7/7] Analisando estabilidade mensal...")

    mensal_2026 = metricas_por_grupo(
        errors_2026,
        "mes",
    )

    mensal_2026 = mensal_2026.sort_values(
        "mes"
    )

    print("\n" + "=" * 90)
    print("PERFORMANCE MENSAL — 2026")
    print("=" * 90)

    print(
        mensal_2026[
            [
                "mes",
                "n",
                "mae_log",
                "rmse_log",
                "medape",
                "wape",
                "unseen_item_rate",
            ]
        ]
        .to_string(
            index=False,
            formatters={
                "mae_log":
                    "{:.6f}".format,
                "rmse_log":
                    "{:.6f}".format,
                "medape":
                    "{:.2f}%".format,
                "wape":
                    "{:.2f}%".format,
                "unseen_item_rate":
                    "{:.2f}%".format,
            },
        )
    )

    # ---------------------------------------------------------
    # Persistir
    # ---------------------------------------------------------
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    overall_path = (
        OUTPUT_DIR
        / "stability_overall_2025_vs_2026.csv"
    )

    cold_path = (
        OUTPUT_DIR
        / "stability_cold_start_2025_vs_2026.csv"
    )

    categoria_path = (
        OUTPUT_DIR
        / "stability_category_2025_vs_2026.csv"
    )

    mix_path = (
        OUTPUT_DIR
        / "drift_category_mix_2025_vs_2026.csv"
    )

    distribuicao_path = (
        OUTPUT_DIR
        / "drift_distribution_2025_vs_2026.csv"
    )

    mensal_path = (
        OUTPUT_DIR
        / "stability_monthly_2026.csv"
    )

    summary_path = (
        OUTPUT_DIR
        / "stability_drift_2026_summary.json"
    )

    overall.to_csv(
        overall_path,
        index=False,
    )

    cold_start.to_csv(
        cold_path,
        index=False,
    )

    categoria_comparacao.to_csv(
        categoria_path,
        index=False,
    )

    mix.to_csv(
        mix_path,
        index=False,
    )

    distribuicoes.to_csv(
        distribuicao_path,
        index=False,
    )

    mensal_2026.to_csv(
        mensal_path,
        index=False,
    )

    maior_shift = (
        mix.sort_values(
            "abs_delta_pp",
            ascending=False,
        )
        .iloc[0]
    )

    summary = {
        "interpretation_note": (
            "2025 e 2026 usam modelos treinados em janelas diferentes; "
            "a comparacao de performance mede estabilidade temporal e "
            "nao deve ser interpretada como estimativa causal pura de drift."
        ),

        "mae_log_2025": float(
            metrics_2025["mae_log"]
        ),

        "mae_log_2026": float(
            metrics_2026["mae_log"]
        ),

        "mae_log_delta_pct": float(
            100
            * (
                metrics_2026["mae_log"]
                / metrics_2025["mae_log"]
                - 1
            )
        ),

        "known_item_rate_2025": float(
            metrics_2025[
                "known_item_rate"
            ]
        ),

        "known_item_rate_2026": float(
            metrics_2026[
                "known_item_rate"
            ]
        ),

        "unseen_item_rate_2025": float(
            metrics_2025[
                "unseen_item_rate"
            ]
        ),

        "unseen_item_rate_2026": float(
            metrics_2026[
                "unseen_item_rate"
            ]
        ),

        "category_mix_tvd_pct": tvd_pct,

        "largest_category_mix_shift": {
            "categoria": str(
                maior_shift[
                    "categoria_relevante"
                ]
            ),
            "delta_pp": float(
                maior_shift["delta_pp"]
            ),
        },
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

    print("\n" + "=" * 90)
    print("ARQUIVOS SALVOS")
    print("=" * 90)

    print(overall_path)
    print(cold_path)
    print(categoria_path)
    print(mix_path)
    print(distribuicao_path)
    print(mensal_path)
    print(summary_path)

    print("\n" + "=" * 90)
    print("FIM — STABILITY & DRIFT ANALYSIS")
    print("=" * 90)


if __name__ == "__main__":
    main()