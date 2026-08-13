import pandas as pd

from src.transformation.silver import (
    apply_typing,
    remove_exact_duplicates,
    resolve_temporal_revisions,
    suppliers_per_item_distribution,
    validate_composite_key,
    parse_unit_canonical, 
    classify_unit_comparability,
    classify_relevant_category, 
    summarize_relevant_categories,
    flag_conflicting_results, 
    compute_spend_total,
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


def test_parse_unit_canonical_extracts_embedded_quantity():
    assert parse_unit_canonical("EMBALAGEM 500,00 G") == ("PESO", 500.0)
    assert parse_unit_canonical("CAIXA 1,00 L") == ("VOLUME", 1000.0)


def test_parse_unit_canonical_handles_bare_words():
    assert parse_unit_canonical("QUILOGRAMA") == ("PESO", 1000.0)
    assert parse_unit_canonical("UNIDADE") == ("CONTAGEM", None)


def test_parse_unit_canonical_returns_none_for_unrecognized():
    assert parse_unit_canonical("ALGO ESTRANHO XYZ") is None


def test_classify_unit_comparability_same_dimension():
    df = pd.DataFrame({
        "descricao_resumida": ["A", "A", "A"],
        "unidade_medida": ["GRAMA", "QUILOGRAMA", "EMBALAGEM 500,00 G"],
    })
    resultado = classify_unit_comparability(df)
    assert (resultado["unit_flag"] == "unit_requires_conversion").all()


def test_classify_unit_comparability_cross_dimension_is_unknown():
    df = pd.DataFrame({
        "descricao_resumida": ["B", "B"],
        "unidade_medida": ["QUILOGRAMA", "UNIDADE"],
    })
    resultado = classify_unit_comparability(df)
    assert (resultado["unit_flag"] == "unit_unknown").all()


def test_classify_unit_comparability_single_unit_is_comparable():
    df = pd.DataFrame({
        "descricao_resumida": ["C", "C", "C"],
        "unidade_medida": ["UNIDADE", "UNIDADE", "UNIDADE"],
    })
    resultado = classify_unit_comparability(df)
    assert (resultado["unit_flag"] == "unit_comparable").all()

def test_classify_relevant_category_matches_known_term():
    df = pd.DataFrame({"descricao_resumida": ["Notebook Dell", "Fruta", "Serviço de Consultoria"]})
    resultado = classify_relevant_category(df)
    assert resultado.loc[0, "categoria_relevante"] == "TI / Informatica"
    assert resultado.loc[1, "categoria_relevante"] is None
    assert resultado.loc[2, "categoria_relevante"] == "Consultoria / Servicos Profissionais"


def test_classify_relevant_category_handles_accents():
    df = pd.DataFrame({"descricao_resumida": ["Cadeira Escritório", "Serviço de Limpeza"]})
    resultado = classify_relevant_category(df)
    assert resultado.loc[0, "categoria_relevante"] == "Mobiliario / Material de Escritorio"
    assert resultado.loc[1, "categoria_relevante"] == "Limpeza / Facilities"


def test_classify_relevant_category_avoids_ambiguous_substring():
    # "servidor" sozinho nao deve capturar "servidor publico" como TI
    df = pd.DataFrame({"descricao_resumida": ["Curso de Capacitação para Servidor Público"]})
    resultado = classify_relevant_category(df)
    assert resultado.loc[0, "categoria_relevante"] is None


def test_summarize_relevant_categories():
    df = pd.DataFrame({"descricao_resumida": ["Notebook", "Fruta", "Notebook", "Consultoria"]})
    df = classify_relevant_category(df)
    resumo = summarize_relevant_categories(df)
    assert resumo["n_categorizado"] == 3
    assert resumo["por_categoria"]["TI / Informatica"] == 2

def test_flag_conflicting_results_detects_same_date_diff_value():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1", "2"],
        "cod_fornecedor": ["10", "10", "20"],
        "data_resultado": pd.to_datetime(["2026-05-22", "2026-05-22", "2026-05-22"]),
        "valor_unitario_resultado": [4.0, 4.2, 9.0],
        "valor_total_resultado": [6600.0, 6930.0, 100.0],
    })
    resultado = flag_conflicting_results(df)
    assert resultado.loc[0, "resultado_conflitante"] is True or resultado.loc[0, "resultado_conflitante"] == True
    assert resultado.loc[1, "resultado_conflitante"] == True
    assert resultado.loc[2, "resultado_conflitante"] == False


def test_flag_conflicting_results_ignores_diff_date_groups():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1"],
        "cod_fornecedor": ["10", "10"],
        "data_resultado": pd.to_datetime(["2026-05-20", "2026-05-22"]),
        "valor_unitario_resultado": [4.0, 4.2],
        "valor_total_resultado": [100.0, 105.0],
    })
    resultado = flag_conflicting_results(df)
    assert not resultado["resultado_conflitante"].any()


def test_compute_spend_total_excludes_conflicting_rows():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1", "2"],
        "cod_fornecedor": ["10", "10", "20"],
        "data_resultado": pd.to_datetime(["2026-05-22", "2026-05-22", "2026-05-22"]),
        "valor_unitario_resultado": [4.0, 4.2, 9.0],
        "valor_total_resultado": [6600.0, 6930.0, 100.0],
    })
    df = flag_conflicting_results(df)
    resultado = compute_spend_total(df)
    assert resultado["spend_total_bruto"] == 13630.0
    assert resultado["spend_total_liquido_sem_conflitos"] == 100.0
    assert resultado["n_linhas_excluidas"] == 2


def test_remove_exact_duplicates_ignores_metadata_timestamps():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1"],
        "cod_fornecedor": ["10", "10"],
        "valor_unitario_resultado": ["63000.0", "63000.0"],
        "quantidade": ["1", "1"],
        "data_resultado": ["2024-12-09", "2024-12-09"],
        "data_atualizacao_pncp": ["2024-12-09", "2025-09-17"],  # difere - so metadado
    })
    df_dedup, stats = remove_exact_duplicates(df)
    assert stats["duplicatas_removidas"] == 1
    assert len(df_dedup) == 1


def test_remove_exact_duplicates_ignores_estimated_value_when_result_matches():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1"],
        "cod_fornecedor": ["10", "10"],
        "valor_unitario_resultado": ["63000.0", "63000.0"],
        "valor_total": ["110051.06", "108000.00"],  # estimativa reeditada entre anos
        "quantidade": ["1", "1"],
        "data_resultado": ["2024-12-09", "2024-12-09"],
    })
    df_dedup, stats = remove_exact_duplicates(df)
    assert stats["duplicatas_removidas"] == 1
    assert len(df_dedup) == 1


def test_remove_exact_duplicates_ignores_supplier_label_and_estimated_quantity():
    df = pd.DataFrame({
        "id_compra_item": ["1", "1"],
        "cod_fornecedor": ["10", "10"],
        "nome_fornecedor": ["Empresa X LTDA", "EMPRESA X LTDA "],
        "quantidade": ["100", "95"],
        "quantidade_resultado": ["100", "100"],
        "valor_unitario_resultado": ["50.0", "50.0"],
        "data_resultado": ["2024-01-01", "2024-01-01"],
    })
    df_dedup, stats = remove_exact_duplicates(df)
    assert stats["duplicatas_removidas"] == 1