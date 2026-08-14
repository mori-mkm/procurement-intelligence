import pandas as pd

from src.analytics.price_baseline import (
    prepare_baseline_dataset,
    split_temporal,
    compute_median_baseline,
    evaluate_baseline,
)


def make_fact_df():
    return pd.DataFrame({
        "item_key": ["notebook"] * 6 + ["mouse"] * 2 + ["fruta"] * 3,
        "unit_price": [
            1000.0, 1100.0, 900.0, 1050.0, 950.0, 1200.0,
            50.0, 55.0,
            10.0, 12.0, 11.0,
        ],
        "quantity": [1.0] * 11,
        "date_key": [
            20240101, 20240201, 20240301,
            20250101, 20260101, 20240401,
            20240101, 20250101,
            20240101, 20240101, 20240101,
        ],
        "categoria_relevante": [
            "TI / Informatica"
        ] * 8 + [None] * 3,
        "is_value_outlier": [False] * 11,
    })


def test_prepare_baseline_dataset_excludes_uncategorized():
    resultado = prepare_baseline_dataset(make_fact_df())
    assert "fruta" not in resultado["item_key"].values
    assert "ano" in resultado.columns
    assert resultado.loc[resultado["item_key"] == "notebook", "ano"].iloc[0] in {2024, 2025, 2026}


def test_split_temporal_separates_by_year():
    df = prepare_baseline_dataset(make_fact_df())
    splits = split_temporal(df)
    assert (splits["treino"]["ano"] == 2024).all()
    assert (splits["validacao"]["ano"] == 2025).all()
    assert (splits["teste"]["ano"] == 2026).all()


def test_compute_median_baseline_flags_low_volume_item():
    df = prepare_baseline_dataset(make_fact_df())
    treino = split_temporal(df)["treino"]
    baseline = compute_median_baseline(treino, min_transacoes=3)

    notebook = baseline[baseline["item_key"] == "notebook"]
    mouse = baseline[baseline["item_key"] == "mouse"]

    assert notebook["baseline_confiavel"].iloc[0] == True
    assert notebook["n_transacoes_treino"].iloc[0] == 4  # 4 no treino (2024)
    assert mouse["baseline_confiavel"].iloc[0] == False  # so 1 no treino


def test_evaluate_baseline_computes_mae_and_coverage():
    df = prepare_baseline_dataset(make_fact_df())
    splits = split_temporal(df)
    baseline = compute_median_baseline(splits["treino"], min_transacoes=3)

    resultado = evaluate_baseline(splits["validacao"], baseline)
    # validacao (2025) tem 2 transacoes: notebook (confiavel) e mouse
    # (nao confiavel, so 1 no treino com min_transacoes=3)
    assert resultado["n_transacoes_total"] == 2
    assert resultado["n_transacoes_com_baseline"] == 1
    assert resultado["pct_cobertura"] == 50.0
    assert resultado["mae"] is not None


def test_evaluate_baseline_handles_empty_evaluable_set():
    df = prepare_baseline_dataset(make_fact_df())
    splits = split_temporal(df)
    baseline = compute_median_baseline(splits["treino"], min_transacoes=3)

    df_vazio = splits["validacao"].iloc[0:0]
    resultado = evaluate_baseline(df_vazio, baseline)
    assert resultado["n_transacoes_total"] == 0
    assert resultado["mae"] is None


def test_prepare_baseline_dataset_excludes_non_positive_price():
    df = make_fact_df()

    df.loc[0, "unit_price"] = 0.0
    df.loc[1, "unit_price"] = -10.0

    resultado = prepare_baseline_dataset(df)

    assert (resultado["unit_price"] > 0).all()

    assert 0 not in resultado.index
    assert 1 not in resultado.index


def test_prepare_baseline_dataset_excludes_non_positive_quantity():
    df = make_fact_df()

    df.loc[0, "quantity"] = 0.0
    df.loc[1, "quantity"] = -1.0

    resultado = prepare_baseline_dataset(df)

    assert (resultado["quantity"] > 0).all()

    assert 0 not in resultado.index
    assert 1 not in resultado.index