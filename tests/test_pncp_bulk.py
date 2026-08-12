from datetime import date
import json

from src.ingestion.pncp_bulk import (
    build_url, 
    local_path_for, 
    DATASET_ITEM, 
    DATASET_COMPRA,
    already_ingested, 
    MANIFEST_PATH, 
    local_path_for,
)

def test_build_url():
    url = build_url(date(2026, 1, 22))
    assert url == (
        "https://repositorio.dados.gov.br/seges/comprasgov/diario/2026/01/22/"
        "comprasGOV-diario-VW_FT_PNCP_COMPRA_ITEM-2026-01-22.csv"
    )


def test_local_path_for():
    path = local_path_for(date(2026, 1, 22))
    assert path.as_posix() == "data/bronze/pncp_compra_item/dt=2026-01-22/comprasGOV-diario-VW_FT_PNCP_COMPRA_ITEM-2026-01-22.csv"

def test_build_url():
    url = build_url(date(2026, 1, 22))
    assert url == (
        "https://repositorio.dados.gov.br/seges/comprasgov/diario/2026/01/22/"
        "comprasGOV-diario-VW_FT_PNCP_COMPRA_ITEM-2026-01-22.csv"
    )


def test_local_path_for():
    path = local_path_for(date(2026, 1, 22))
    assert path.as_posix() == "data/bronze/pncp_compra_item/dt=2026-01-22/comprasGOV-diario-VW_FT_PNCP_COMPRA_ITEM-2026-01-22.csv"


def test_build_url_compra_dataset():
    url = build_url(date(2026, 1, 22), dataset=DATASET_COMPRA)
    assert url == (
        "https://repositorio.dados.gov.br/seges/comprasgov/diario/2026/01/22/"
        "comprasGOV-diario-VW_FT_PNCP_COMPRA-2026-01-22.csv"
    )


def test_local_path_for_compra_dataset():
    path = local_path_for(date(2026, 1, 22), dataset=DATASET_COMPRA)
    assert path.as_posix() == "data/bronze/pncp_compra/dt=2026-01-22/comprasGOV-diario-VW_FT_PNCP_COMPRA-2026-01-22.csv"

def test_already_ingested_treats_missing_dataset_as_item(tmp_path, monkeypatch):
    """Registros gravados antes da mudança multi-dataset (sem campo 'dataset')
    devem continuar sendo reconhecidos como DATASET_ITEM — senão a
    idempotência quebra silenciosamente para todo o historico ja baixado."""
    manifest_path = tmp_path / "ingestion_log.jsonl"
    monkeypatch.setattr("src.ingestion.pncp_bulk.MANIFEST_PATH", manifest_path)

    alvo = date(2026, 1, 22)
    caminho = local_path_for(alvo)  # dataset default = item
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"conteudo de teste")
    tamanho_real = caminho.stat().st_size

    # Simula um registro antigo, sem campo "dataset" (formato pre-mudanca)
    registro_antigo = {
        "data_referencia": "2026-01-22",
        "url": "https://exemplo.com",
        "status": "success",
        "caminho_local": str(caminho),
        "tamanho_bytes": tamanho_real,
        "n_linhas": 100,
        "data_ingestao_utc": "2026-01-22T00:00:00+00:00",
        "detalhe_erro": None,
    }
    manifest_path.write_text(json.dumps(registro_antigo) + "\n", encoding="utf-8")

    assert already_ingested(alvo) is True

    caminho.unlink()