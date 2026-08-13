import pandas as pd

from src.quality.checks import (
    basic_shape,
    exact_duplicates,
    key_duplicates,
    value_range_check,
    missing_reference_check,
    unit_heterogeneity,
    schema_drift_check,
    select_necessary_columns,
    normalize_legacy_column_names,
)


def make_sample_df():
    return pd.DataFrame({
        "id_compra_item": [1, 2, 2, 3, 4],
        "cod_fornecedor": [10, 20, 20, None, 40],
        "cod_item_catalogo": [100, 100, 100, None, 200],
        "unidade_medida": ["UN", "UN", "CX", "UN", "KG"],
        "valor_unitario_resultado": [5.0, -1.0, 0.0, 10.0, 3.0],
        "quantidade": [1, 2, 2, 0, 5],
    })


def test_basic_shape():
    df = make_sample_df()
    shape = basic_shape(df)
    assert shape["n_linhas"] == 5
    assert shape["n_colunas"] == 6


def test_exact_duplicates_none():
    assert exact_duplicates(make_sample_df())["n_duplicatas_exatas"] == 0


def test_key_duplicates_detects_repeated_id():
    result = key_duplicates(make_sample_df(), "id_compra_item")
    assert result["n_duplicados"] == 1


def test_value_range_check_flags_negative_and_zero():
    result = value_range_check(make_sample_df(), "valor_unitario_resultado")
    assert result["n_abaixo_de_0"] == 1
    assert result["n_igual_a_zero"] == 1


def test_missing_reference_check():
    result = missing_reference_check(make_sample_df(), "cod_fornecedor")
    assert result["n_ausente"] == 1


def test_unit_heterogeneity_detects_multi_unit_item():
    result = unit_heterogeneity(make_sample_df(), "cod_item_catalogo", "unidade_medida")
    assert result["n_itens_com_multiplas_unidades"] == 1


def test_schema_drift_check_detects_new_and_missing_columns():
    referencia = ["a", "b", "c"]
    df = pd.DataFrame(columns=["a", "b", "d"])
    result = schema_drift_check(df, referencia)
    assert result["schema_bate"] is False
    assert result["colunas_novas"] == ["d"]
    assert result["colunas_ausentes"] == ["c"]


def test_schema_drift_check_no_drift():
    referencia = ["a", "b"]
    df = pd.DataFrame(columns=["a", "b"])
    result = schema_drift_check(df, referencia)
    assert result["schema_bate"] is True
    assert result["colunas_novas"] == []
    assert result["colunas_ausentes"] == []

def test_load_bronze_csv_preserves_id_leading_zeros(tmp_path):
    from src.quality.checks import load_bronze_csv

    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "id_compra_item,cod_fornecedor,valor_unitario_resultado\n"
        "1,00123456000199,10.5\n",
        encoding="utf-8",
    )
    df = load_bronze_csv(csv_path)
    assert df["cod_fornecedor"].iloc[0] == "00123456000199"

def test_list_multi_unit_items_sorts_by_transaction_volume():
    from src.quality.checks import list_multi_unit_items

    df = pd.DataFrame({
        "descricao_resumida": ["A", "A", "A", "B", "B", "C"],
        "unidade_medida": ["UN", "CX", "UN", "KG", "L", "UN"],
        "cod_item_catalogo": [None, None, None, None, None, None],
    })
    resultado = list_multi_unit_items(df, top_n=10)
    assert len(resultado) == 2  # A e B têm múltiplas unidades; C não
    assert resultado[0]["item"] == "A"
    assert resultado[0]["n_transacoes"] == 3


def test_select_necessary_columns_keeps_only_relevant():
    df = pd.DataFrame({
        "id_compra_item": ["1"],
        "descricao_resumida": ["Notebook"],
        "TXT_LINK_MATERIAL": ["http://exemplo.com"],
    })
    resultado = select_necessary_columns(df)
    assert "TXT_LINK_MATERIAL" not in resultado.columns
    assert "id_compra_item" in resultado.columns
    assert "descricao_resumida" in resultado.columns


def test_normalize_legacy_column_names_renames_when_canonical_absent():
    df = pd.DataFrame({"descricao": ["Notebook"], "data_inclusao": ["2024-01-01"]})
    resultado = normalize_legacy_column_names(df)
    assert "descricao_resumida" in resultado.columns
    assert "descricao" not in resultado.columns


def test_normalize_legacy_column_names_never_overwrites_canonical():
    df = pd.DataFrame({"descricao": ["Legado"], "descricao_resumida": ["Real"]})
    resultado = normalize_legacy_column_names(df)
    assert resultado["descricao_resumida"].iloc[0] == "Real"