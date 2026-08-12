from src.ingestion.pncp_bulk_annual import (
    build_annual_url, 
    local_parquet_path, 
    DATASET_COMPRA,
    _default_id_columns_for, 
    DATASET_ITEM,
    _build_types_clause,
)


def test_build_annual_url():
    url = build_annual_url(2025, DATASET_COMPRA)
    assert url == (
        "https://repositorio.dados.gov.br/seges/comprasgov/anual/2025/"
        "comprasGOV-anual-VW_FT_PNCP_COMPRA-2025.csv"
    )


def test_local_parquet_path():
    path = local_parquet_path(2025, DATASET_COMPRA)
    assert path.as_posix() == "data/bronze/pncp_compra_anual/ano=2025/VW_FT_PNCP_COMPRA-2025.parquet"



def test_default_id_columns_for_item_dataset_not_empty():
    cols = _default_id_columns_for(DATASET_ITEM)
    assert "cod_fornecedor" in cols
    assert "id_compra_item" in cols
    assert len(cols) > 0


def test_default_id_columns_for_compra_dataset():
    cols = _default_id_columns_for(DATASET_COMPRA)
    assert "orgao_entidade_cnpj" in cols



def test_build_types_clause_deduplicates_columns():
    clausula = _build_types_clause(["id_compra", "cod_compra", "id_compra"])
    assert clausula.count("'id_compra'") == 1