from src.ingestion.pncp_bulk_annual import build_annual_url, local_parquet_path, DATASET_COMPRA


def test_build_annual_url():
    url = build_annual_url(2025, DATASET_COMPRA)
    assert url == (
        "https://repositorio.dados.gov.br/seges/comprasgov/anual/2025/"
        "comprasGOV-anual-VW_FT_PNCP_COMPRA-2025.csv"
    )


def test_local_parquet_path():
    path = local_parquet_path(2025, DATASET_COMPRA)
    assert path.as_posix() == "data/bronze/pncp_compra_anual/ano=2025/VW_FT_PNCP_COMPRA-2025.parquet"