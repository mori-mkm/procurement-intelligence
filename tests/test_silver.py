import pandas as pd

from src.transformation.silver import (
    apply_typing,
    remove_exact_duplicates,
    resolve_temporal_revisions,
    suppliers_per_item_distribution,
    validate_composite_key,
)


def make_sample_df():
    return pd.DataFrame({
        "id_compra_item": ["1", "1", "2", "2", "2"],
        "cod_fornecedor": ["10", "10", "20", "20", "30"],
        "valor_unitario_resultado": ["5.0", "5.0", "3.0", "3.0", "7.0"],
        "quantidade": ["2", "2", "1", "1", "1"],
        "data_resultado": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02", "2026-01-03"],
        "COD_RESULTADO_ITEM": ["100", "101", "200", "200", "300"],
    })


def test_apply_typing_converts_numeric_and_date():
    df = apply_typing(make_sample_df())
    assert pd.api.types.is_numeric_dtype(df["valor_unitario_resultado"])
    assert pd.api.types.is_numeric_dtype(df["quantidade"])
    assert pd.api.types.is_datetime64_any_dtype(df["data_resultado"])


def test_remove_exact_duplicates():
    df_dedup, stats = remove_exact_duplicates(make_sample_df())
    assert stats["linhas_antes"] == 5
    assert stats["duplicatas_removidas"] == 2
    assert stats["linhas_depois"] == 3


def test_suppliers_per_item_distribution_after_dedup():
    df_dedup, _ = remove_exact_duplicates(make_sample_df())
    dist = suppliers_per_item_distribution(df_dedup)
    assert dist["n_itens_distintos"] == 2
    assert dist["n_itens_com_multiplos_fornecedores"] == 1


def test_validate_composite_key_unique_after_dedup():
    df_dedup, _ = remove_exact_duplicates(make_sample_df())
    resultado = validate_composite_key(df_dedup)
    assert resultado["chave_e_unica"] is True
    assert resultado["n_violacoes"] == 0


def test_validate_composite_key_detects_violation():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1"],
        "cod_fornecedor": ["10", "10"],
        "valor_unitario_resultado": ["5.0", "6.0"],
        "quantidade": ["1", "1"],
        "data_resultado": ["2026-01-01", "2026-01-01"],
    })
    resultado = validate_composite_key(df)
    assert resultado["chave_e_unica"] is False
    assert resultado["n_violacoes"] == 1
    assert "amostra_casos_problematicos" in resultado


def test_resolve_temporal_revisions_keeps_most_recent():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1", "2"],
        "cod_fornecedor": ["10", "10", "20"],
        "valor_unitario_resultado": [10.0, 12.0, 5.0],
        "data_resultado": pd.to_datetime(["2026-01-01", "2026-01-05", "2026-01-02"]),
    })
    df_resolvido, stats = resolve_temporal_revisions(df)
    assert len(df_resolvido) == 2
    assert stats["revisoes_temporais_resolvidas"] == 1
    linha_1 = df_resolvido[df_resolvido["id_compra_item"] == "1"]
    assert linha_1["valor_unitario_resultado"].iloc[0] == 12.0


def test_resolve_temporal_revisions_leaves_same_date_conflicts_untouched():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1"],
        "cod_fornecedor": ["10", "10"],
        "valor_unitario_resultado": [10.0, 12.0],
        "data_resultado": pd.to_datetime(["2026-01-01", "2026-01-01"]),
    })
    df_resolvido, stats = resolve_temporal_revisions(df)
    assert len(df_resolvido) == 2
    assert stats["revisoes_temporais_resolvidas"] == 0