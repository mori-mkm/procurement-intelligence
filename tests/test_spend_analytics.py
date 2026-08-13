import pandas as pd

from src.analytics.spend_analytics import (
    classify_hhi,
    compute_spend_by_category,
    compute_hhi_by_category,
    build_supplier_abc_curve,
    CATEGORIA_NAO_CLASSIFICADA,
    flag_extreme_by_global_median,
)


def make_fact_df():
    return pd.DataFrame({
        "supplier_key": ["A", "A", "B", "C", "D"],
        "item_key": ["notebook", "notebook", "mouse", "cadeira", "fruta"],
        "categoria_relevante": ["TI / Informatica", "TI / Informatica", "TI / Informatica", "Mobiliario", None],
        "total_price": [1000.0, 500.0, 300.0, 200.0, 50.0],
    })


def test_classify_hhi_thresholds():
    assert classify_hhi(1000) == "nao concentrado"
    assert classify_hhi(2000) == "moderadamente concentrado"
    assert classify_hhi(3000) == "altamente concentrado"


def test_compute_spend_by_category_groups_null_as_nao_classificado():
    resultado = compute_spend_by_category(make_fact_df())
    categorias = set(resultado["categoria_relevante"])
    assert CATEGORIA_NAO_CLASSIFICADA in categorias
    linha_ti = resultado[resultado["categoria_relevante"] == "TI / Informatica"]
    assert linha_ti["spend_total"].iloc[0] == 1800.0
    assert linha_ti["n_fornecedores_distintos"].iloc[0] == 2


def test_compute_spend_by_category_percentages_sum_to_100():
    resultado = compute_spend_by_category(make_fact_df())
    assert abs(resultado["pct_do_spend_total"].sum() - 100.0) < 0.01


def test_compute_hhi_by_category_full_monopoly_is_10000():
    df = pd.DataFrame({
        "supplier_key": ["A", "A"],
        "categoria_relevante": ["X", "X"],
        "total_price": [100.0, 200.0],
    })
    resultado = compute_hhi_by_category(df)
    assert resultado["hhi"].iloc[0] == 10000.0
    assert resultado["classificacao_hhi"].iloc[0] == "altamente concentrado"


def test_compute_hhi_by_category_two_equal_suppliers_is_5000():
    df = pd.DataFrame({
        "supplier_key": ["A", "B"],
        "categoria_relevante": ["X", "X"],
        "total_price": [100.0, 100.0],
    })
    resultado = compute_hhi_by_category(df)
    assert resultado["hhi"].iloc[0] == 5000.0


def test_build_supplier_abc_curve_classifies_by_cumulative_share():
    # Fornecedor A soma 1500 de 1800 na categoria (83,3%) -- ultrapassa o
    # corte de 80% sozinho, cai em Classe B pela definicao de build_supplier_abc_curve
    # (classe A = cum_share_pct <= 80). Fornecedor B fecha o resto (16,7%,
    # cumulativo 100%) -- tambem B, pois cum_share_pct <= 95.
    resultado = build_supplier_abc_curve(make_fact_df(), category="TI / Informatica")
    assert resultado.iloc[0]["supplier_key"] == "A"
    assert round(resultado.iloc[0]["share_pct"], 1) == 83.3
    assert resultado.iloc[0]["classe_abc"] == "B"
    assert set(resultado["classe_abc"]).issubset({"A", "B", "C"})


def test_build_supplier_abc_curve_empty_category_returns_empty_df():
    resultado = build_supplier_abc_curve(make_fact_df(), category="Categoria Inexistente")
    assert len(resultado) == 0


def test_compute_spend_by_category_excludes_flagged_outliers():
    df = make_fact_df()
    df["is_value_outlier"] = [False, False, False, False, True]  # exclui a linha "fruta"
    resultado = compute_spend_by_category(df)
    categorias = set(resultado["categoria_relevante"])
    assert CATEGORIA_NAO_CLASSIFICADA not in categorias  # so linha excluida era essa categoria


def test_flag_extreme_by_global_median_catches_escaped_outlier():
    df = pd.DataFrame({
        "total_price": [100.0, 200.0, 150.0, 180.0, 50_000_000.0],
        "is_value_outlier": [False, False, False, False, False],  # escapou da 1a camada
    })
    extremo = flag_extreme_by_global_median(df, multiplier=1000.0)
    assert extremo.iloc[-1] == True
    assert extremo.iloc[:-1].sum() == 0