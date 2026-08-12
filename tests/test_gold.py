from datetime import date
import pandas as pd

from src.transformation.gold import (
    build_dim_buyer,
    validate_dim_buyer_grain,
    join_fact_with_buyer,
    load_dim_buyer_from_annual,
    resolve_duplicate_buyer_records,
    normalize_item_key,
    build_dim_item,
    build_dim_supplier,
    build_dim_date,
    build_fact_purchase,
    validate_fact_purchase_grain,
    _most_frequent_per_group,
    save_gold_layer, 
    load_gold_layer
)


def make_cabecalho_df():
    return pd.DataFrame({
        "id_compra": ["1", "2"],
        "orgao_entidade_cnpj": ["00394502000144", "12345678000199"],
        "orgao_entidade_razao_social": ["COMANDO DA MARINHA", "OUTRO ORGAO"],
        "unidade_orgao_uf_sigla": ["RJ", "SP"],
        "unidade_orgao_municipio_nome": ["Rio de Janeiro", "Sao Paulo"],
        "codigo_modalidade": [8, 6],
        "modalidade_nome": ["Dispensa", "Pregão - Eletrônico"],
    })


# ---------------------------------------------------------------------------
# dim_buyer (diário)
# ---------------------------------------------------------------------------

def test_build_dim_buyer_selects_expected_columns():
    dim_buyer = build_dim_buyer(make_cabecalho_df())
    assert list(dim_buyer.columns) == [
        "id_compra", "orgao_entidade_cnpj", "orgao_entidade_razao_social",
        "unidade_orgao_uf_sigla", "unidade_orgao_municipio_nome",
        "codigo_modalidade", "modalidade_nome",
    ]


def test_build_dim_buyer_raises_on_missing_column():
    df_incompleto = make_cabecalho_df().drop(columns=["modalidade_nome"])
    try:
        build_dim_buyer(df_incompleto)
        assert False, "deveria ter levantado ValueError"
    except ValueError as e:
        assert "modalidade_nome" in str(e)


def test_validate_dim_buyer_grain_detects_unique():
    dim_buyer = build_dim_buyer(make_cabecalho_df())
    resultado = validate_dim_buyer_grain(dim_buyer)
    assert resultado["grao_valido"] is True
    assert resultado["id_compra_duplicado"] == 0


def test_validate_dim_buyer_grain_detects_duplicate():
    df_dup = pd.concat([make_cabecalho_df(), make_cabecalho_df().iloc[[0]]], ignore_index=True)
    dim_buyer = build_dim_buyer(df_dup)
    resultado = validate_dim_buyer_grain(dim_buyer)
    assert resultado["grao_valido"] is False
    assert resultado["id_compra_duplicado"] == 1


def test_join_fact_with_buyer_preserves_row_count():
    dim_buyer = build_dim_buyer(make_cabecalho_df())
    df_fact = pd.DataFrame({
        "id_compra_item": ["a1", "a2", "b1"],
        "id_compra": ["1", "1", "2"],
        "valor_total_resultado": [100.0, 200.0, 300.0],
    })
    resultado, stats = join_fact_with_buyer(df_fact, dim_buyer)
    assert len(resultado) == 3
    assert stats["linhas_sem_match_no_buyer"] == 0
    assert resultado.loc[resultado["id_compra"] == "1", "unidade_orgao_uf_sigla"].iloc[0] == "RJ"


def test_join_fact_with_buyer_handles_missing_match():
    dim_buyer = build_dim_buyer(make_cabecalho_df())
    df_fact = pd.DataFrame({
        "id_compra_item": ["x1", "y1"],
        "id_compra": ["999", "1"],  # "999" não existe em dim_buyer, "1" existe
        "orgao_entidade_cnpj": ["12312312312312", "00394502000144"],  # já vem do item, nunca é nulo
        "valor_total_resultado": [50.0, 60.0],
    })
    resultado, stats = join_fact_with_buyer(df_fact, dim_buyer)
    assert stats["linhas_sem_match_no_buyer"] == 1  # só "999" deveria contar
    assert pd.isna(resultado.loc[resultado["id_compra"] == "999", "unidade_orgao_uf_sigla"].iloc[0])
    assert resultado.loc[resultado["id_compra"] == "1", "unidade_orgao_uf_sigla"].iloc[0] == "RJ"


# ---------------------------------------------------------------------------
# dim_buyer (anual, multi-ano)
# ---------------------------------------------------------------------------

def test_load_dim_buyer_from_annual_raises_if_missing(tmp_path, monkeypatch):
    import src.ingestion.pncp_bulk_annual as annual_module
    monkeypatch.setattr(annual_module, "BRONZE_ANNUAL_ROOT", tmp_path)
    try:
        load_dim_buyer_from_annual([2099])
        assert False, "deveria ter levantado FileNotFoundError"
    except FileNotFoundError:
        pass


def test_load_dim_buyer_from_annual_reads_and_builds(tmp_path, monkeypatch):
    import src.ingestion.pncp_bulk_annual as annual_module
    monkeypatch.setattr(annual_module, "BRONZE_ANNUAL_ROOT", tmp_path)

    caminho = annual_module.local_parquet_path(2025, annual_module.DATASET_COMPRA)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "id_compra": ["1"],
        "data_publicacao_pncp": ["2025-01-01"],
        "orgao_entidade_cnpj": ["00394502000144"],
        "orgao_entidade_razao_social": ["COMANDO DA MARINHA"],
        "unidade_orgao_uf_sigla": ["RJ"],
        "unidade_orgao_municipio_nome": ["Rio de Janeiro"],
        "codigo_modalidade": [8],
        "modalidade_nome": ["Dispensa"],
    }).to_parquet(caminho)

    dim_buyer = load_dim_buyer_from_annual([2025])
    assert len(dim_buyer) == 1
    assert dim_buyer["id_compra"].iloc[0] == "1"


def test_resolve_duplicate_buyer_records_keeps_most_recent():
    df = pd.DataFrame({
        "id_compra": ["1", "1", "2"],
        "data_publicacao_pncp": pd.to_datetime(["2024-05-07", "2024-06-06", "2025-01-01"]),
        "orgao_entidade_razao_social": ["A", "A", "B"],
    })
    resultado, stats = resolve_duplicate_buyer_records(df)
    assert len(resultado) == 2
    assert stats["duplicatas_removidas"] == 1
    linha_1 = resultado[resultado["id_compra"] == "1"]
    assert linha_1["data_publicacao_pncp"].iloc[0] == pd.Timestamp("2024-06-06")


def test_load_dim_buyer_from_annual_deduplicates_across_years(tmp_path, monkeypatch):
    import src.ingestion.pncp_bulk_annual as annual_module
    monkeypatch.setattr(annual_module, "BRONZE_ANNUAL_ROOT", tmp_path)

    base_cols = {
        "orgao_entidade_cnpj": ["00394502000144"],
        "orgao_entidade_razao_social": ["COMANDO DA MARINHA"],
        "unidade_orgao_uf_sigla": ["RJ"],
        "unidade_orgao_municipio_nome": ["Rio de Janeiro"],
        "codigo_modalidade": [8],
        "modalidade_nome": ["Dispensa"],
    }
    caminho_2024 = annual_module.local_parquet_path(2024, annual_module.DATASET_COMPRA)
    caminho_2024.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"id_compra": ["1"], "data_publicacao_pncp": ["2024-12-20"], **base_cols}).to_parquet(caminho_2024)

    caminho_2025 = annual_module.local_parquet_path(2025, annual_module.DATASET_COMPRA)
    caminho_2025.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"id_compra": ["1"], "data_publicacao_pncp": ["2025-01-05"], **base_cols}).to_parquet(caminho_2025)

    dim_buyer = load_dim_buyer_from_annual([2024, 2025])
    assert len(dim_buyer) == 1  # deduplicado, não 2


# ---------------------------------------------------------------------------
# dim_item
# ---------------------------------------------------------------------------

def test_normalize_item_key_lowercases_and_strips_accents():
    assert normalize_item_key("Cadeira Escritório") == "cadeira escritorio"


def test_normalize_item_key_collapses_whitespace():
    assert normalize_item_key("  Arroz   Beneficiado  ") == "arroz beneficiado"


def test_normalize_item_key_handles_null():
    assert normalize_item_key(None) is None


def test_build_dim_item_merges_case_and_accent_variants():
    df = pd.DataFrame({
        "descricao_resumida": ["Cadeira Escritório", "cadeira escritorio", "Mesa"],
        "cod_item_catalogo": [None, "123", None],
        "material_ou_servico_nome": ["Material", "Material", "Material"],
        "unidade_medida": ["Unidade", "Unidade", "Unidade"],
        "categoria_relevante": ["Mobiliario / Material de Escritorio", "Mobiliario / Material de Escritorio", None],
    })
    dim_item = build_dim_item(df)
    assert len(dim_item) == 2
    linha_cadeira = dim_item[dim_item["item_key"] == "cadeira escritorio"]
    assert linha_cadeira["n_transacoes"].iloc[0] == 2
    assert linha_cadeira["cod_item_catalogo_mais_frequente"].iloc[0] == "123"


def test_build_dim_item_flags_multiple_catmats_without_hiding():
    df = pd.DataFrame({
        "descricao_resumida": ["Fruta", "Fruta", "Fruta"],
        "cod_item_catalogo": ["100", "200", "300"],
        "material_ou_servico_nome": ["Material"] * 3,
        "unidade_medida": ["Quilograma"] * 3,
        "categoria_relevante": [None] * 3,
    })
    dim_item = build_dim_item(df)
    assert dim_item["n_catmats_distintos_observados"].iloc[0] == 3


# ---------------------------------------------------------------------------
# dim_supplier
# ---------------------------------------------------------------------------

def test_build_dim_supplier_counts_distinct_products_not_transactions():
    df = pd.DataFrame({
        "cod_fornecedor": ["123", "123", "123", "456"],
        "nome_fornecedor": ["Empresa A", "Empresa A", "Empresa A", "Empresa B"],
        "descricao_resumida": ["Notebook", "Notebook", "Mouse", "Cadeira"],
    })
    dim_supplier = build_dim_supplier(df)
    linha_a = dim_supplier[dim_supplier["supplier_key"] == "123"]
    assert linha_a["n_transacoes"].iloc[0] == 3
    assert linha_a["n_produtos_servicos_distintos"].iloc[0] == 2  # Notebook, Mouse


# ---------------------------------------------------------------------------
# dim_date
# ---------------------------------------------------------------------------

def test_build_dim_date_covers_range():
    dim_date = build_dim_date(date(2024, 1, 1), date(2024, 1, 3))
    assert len(dim_date) == 3
    assert dim_date["date_key"].iloc[0] == 20240101
    assert dim_date["ano"].iloc[0] == 2024
    assert dim_date["trimestre"].iloc[0] == 1
    assert dim_date["nome_mes"].iloc[0] == "Janeiro"


def test_normalize_item_key_applies_known_typo_correction():
    a = normalize_item_key("Assistência médica complementar desaúde")
    b = normalize_item_key("Assistência médica complementar de saúde")
    assert a == b


# ---------------------------------------------------------------------------
# fact_purchase
# ---------------------------------------------------------------------------

def make_dim_item_df():
    return pd.DataFrame({
        "item_key": ["notebook", "mouse"],
        "unit_flag": ["unit_comparable", "unit_comparable"],
        "cod_item_catalogo_mais_frequente": ["123", None],
    })


def test_build_fact_purchase_assembles_expected_columns():
    dim_buyer = build_dim_buyer(make_cabecalho_df())
    dim_item = make_dim_item_df()
    df_item = pd.DataFrame({
        "id_compra_item": ["a1", "a2"],
        "id_compra": ["1", "2"],
        "cod_fornecedor": ["10", "20"],
        "descricao_resumida": ["Notebook", "Mouse"],
        "data_resultado": pd.to_datetime(["2026-05-22", "2026-05-23"]),
        "quantidade_resultado": [1.0, 2.0],
        "valor_unitario_resultado": [3000.0, 50.0],
        "valor_total_resultado": [3000.0, 100.0],
        "categoria_relevante": ["TI / Informatica", None],
        "resultado_conflitante": [False, False],
    })
    fact, stats = build_fact_purchase(df_item, dim_buyer, dim_item)
    assert len(fact) == 2
    linha_a1 = fact[fact["purchase_item_id"] == "a1"]
    assert linha_a1["unit_flag"].iloc[0] == "unit_comparable"
    assert linha_a1["date_key"].iloc[0] == 20260522
    assert linha_a1["buyer_key"].iloc[0] == "00394502000144"
    assert linha_a1["unidade_orgao_uf_sigla"].iloc[0] == "RJ"


def test_validate_fact_purchase_grain_allows_flagged_violations():
    df = pd.DataFrame({
        "purchase_item_id": ["a1", "a1", "b1"],
        "supplier_key": ["10", "10", "20"],
        "resultado_conflitante": [True, True, False],
    })
    resultado = validate_fact_purchase_grain(df)
    assert resultado["n_violacoes_totais"] == 1
    assert resultado["n_grupos_violacao_nao_flagados"] == 0
    assert resultado["grao_valido_considerando_flags"] is True


def test_validate_fact_purchase_grain_detects_unexpected_violation():
    df = pd.DataFrame({
        "purchase_item_id": ["a1", "a1"],
        "supplier_key": ["10", "10"],
        "resultado_conflitante": [False, False],
    })
    resultado = validate_fact_purchase_grain(df)
    assert resultado["n_grupos_violacao_nao_flagados"] == 1
    assert resultado["grao_valido_considerando_flags"] is False


def test_most_frequent_per_group_picks_higher_count():
    df = pd.DataFrame({
        "grupo": ["a", "a", "a", "b"],
        "valor": ["x", "x", "y", "z"],
    })
    resultado = _most_frequent_per_group(df, "grupo", "valor")
    assert resultado["a"] == "x"
    assert resultado["b"] == "z"


def test_most_frequent_per_group_ignores_nulls():
    df = pd.DataFrame({
        "grupo": ["a", "a"],
        "valor": [None, "x"],
    })
    resultado = _most_frequent_per_group(df, "grupo", "valor")
    assert resultado["a"] == "x"


# ---------------------------------------------------------------------------
# persistência do Gold
# ---------------------------------------------------------------------------

def make_minimal_gold_tables():
    dim_buyer = pd.DataFrame({"id_compra": ["1"], "orgao_entidade_cnpj": ["123"]})
    dim_item = pd.DataFrame({"item_key": ["notebook"], "n_transacoes": [1]})
    dim_supplier = pd.DataFrame({"supplier_key": ["10"], "n_transacoes": [1]})
    dim_date = pd.DataFrame({"date_key": [20250101], "ano": [2025]})
    fact = pd.DataFrame({"purchase_item_id": ["a1"], "supplier_key": ["10"]})
    return dim_buyer, dim_item, dim_supplier, dim_date, fact


def test_save_gold_layer_writes_parquet_files(tmp_path):
    dim_buyer, dim_item, dim_supplier, dim_date, fact = make_minimal_gold_tables()
    stats = save_gold_layer(dim_buyer, dim_item, dim_supplier, dim_date, fact, gold_root=tmp_path)

    assert (tmp_path / "dim_buyer.parquet").exists()
    assert (tmp_path / "fact_purchase.parquet").exists()
    assert stats["n_linhas_fact"] == 1
    assert (tmp_path / "_manifest" / "gold_build_log.jsonl").exists()


def test_load_gold_layer_roundtrip(tmp_path):
    dim_buyer, dim_item, dim_supplier, dim_date, fact = make_minimal_gold_tables()
    save_gold_layer(dim_buyer, dim_item, dim_supplier, dim_date, fact, gold_root=tmp_path)

    carregado = load_gold_layer(gold_root=tmp_path)
    assert set(carregado.keys()) == {"dim_buyer", "dim_item", "dim_supplier", "dim_date", "fact_purchase"}
    assert len(carregado["fact_purchase"]) == 1
    assert carregado["dim_buyer"]["id_compra"].iloc[0] == "1"


def test_load_gold_layer_raises_if_missing(tmp_path):
    try:
        load_gold_layer(gold_root=tmp_path)
        assert False, "deveria ter levantado FileNotFoundError"
    except FileNotFoundError:
        pass