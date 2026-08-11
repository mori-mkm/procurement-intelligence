from datetime import date
from src.ingestion.pncp_bulk import build_url, local_path_for


def test_build_url():
    url = build_url(date(2026, 1, 22))
    assert url == (
        "https://repositorio.dados.gov.br/seges/comprasgov/diario/2026/01/22/"
        "comprasGOV-diario-VW_FT_PNCP_COMPRA_ITEM-2026-01-22.csv"
    )


def test_local_path_for():
    path = local_path_for(date(2026, 1, 22))
    assert path.as_posix() == "data/bronze/pncp_compra_item/dt=2026-01-22/comprasGOV-diario-VW_FT_PNCP_COMPRA_ITEM-2026-01-22.csv"