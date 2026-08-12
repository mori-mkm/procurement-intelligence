"""
Ingestão do arquivo bulk diário do PNCP/compras.gov.br.
Suporta múltiplos datasets: VW_FT_PNCP_COMPRA_ITEM (item, default) e
VW_FT_PNCP_COMPRA (cabeçalho da compra — UF, modalidade, razão social).

Referência: docs/adr/ e fase0_design_procurement_intelligence.md
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

BASE_BULK = "https://repositorio.dados.gov.br/seges/comprasgov"

DATASET_ITEM = "VW_FT_PNCP_COMPRA_ITEM"
DATASET_COMPRA = "VW_FT_PNCP_COMPRA"

_FOLDER_BY_DATASET = {
    DATASET_ITEM: "pncp_compra_item",
    DATASET_COMPRA: "pncp_compra",
}

BRONZE_ROOT = Path("data/bronze")
MANIFEST_PATH = Path("data/bronze") / "_manifest" / "ingestion_log.jsonl"


@dataclass
class IngestionRecord:
    dataset: str
    data_referencia: str
    url: str
    status: str
    caminho_local: Optional[str]
    tamanho_bytes: Optional[int]
    n_linhas: Optional[int]
    data_ingestao_utc: str
    detalhe_erro: Optional[str] = None


def build_url(data_referencia: date, dataset: str = DATASET_ITEM) -> str:
    ano, mes, dia = data_referencia.strftime("%Y"), data_referencia.strftime("%m"), data_referencia.strftime("%d")
    return f"{BASE_BULK}/diario/{ano}/{mes}/{dia}/comprasGOV-diario-{dataset}-{ano}-{mes}-{dia}.csv"


def local_path_for(data_referencia: date, dataset: str = DATASET_ITEM) -> Path:
    ano, mes, dia = data_referencia.strftime("%Y"), data_referencia.strftime("%m"), data_referencia.strftime("%d")
    pasta = _FOLDER_BY_DATASET.get(dataset, dataset.lower())
    filename = f"comprasGOV-diario-{dataset}-{ano}-{mes}-{dia}.csv"
    return BRONZE_ROOT / pasta / f"dt={ano}-{mes}-{dia}" / filename


def read_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    with MANIFEST_PATH.open(encoding="utf-8-sig") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_manifest(record: IngestionRecord) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def already_ingested(data_referencia: date, dataset: str = DATASET_ITEM) -> bool:
    alvo = data_referencia.strftime("%Y-%m-%d")
    caminho = local_path_for(data_referencia, dataset)
    if not caminho.exists():
        return False
    tamanho_local = caminho.stat().st_size
    for reg in reversed(read_manifest()):
        dataset_do_registro = reg.get("dataset", DATASET_ITEM)
        if dataset_do_registro == dataset and reg["data_referencia"] == alvo and reg["status"] == "success":
            if reg.get("tamanho_bytes") == tamanho_local:
                return True
            logger.warning(
                "Registro de sucesso para %s/%s, mas tamanho local (%d) != manifesto (%s) — vou re-baixar.",
                dataset, alvo, tamanho_local, reg.get("tamanho_bytes"),
            )
            return False
    return False


def count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f) - 1


def download_bulk_csv(
    data_referencia: date, dataset: str = DATASET_ITEM, force: bool = False, timeout: int = 60
) -> IngestionRecord:
    alvo = data_referencia.strftime("%Y-%m-%d")
    url = build_url(data_referencia, dataset)
    caminho = local_path_for(data_referencia, dataset)

    if not force and already_ingested(data_referencia, dataset):
        logger.info("Já ingerido e válido: %s/%s (%s) — pulando.", dataset, alvo, caminho)
        record = IngestionRecord(
            dataset=dataset, data_referencia=alvo, url=url, status="skipped_existing",
            caminho_local=str(caminho), tamanho_bytes=caminho.stat().st_size,
            n_linhas=None, data_ingestao_utc=datetime.now(timezone.utc).isoformat(),
        )
        append_manifest(record)
        return record

    logger.info("Baixando %s", url)
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.exceptions.RequestException as e:
        logger.error("Falha de rede: %s", e)
        record = IngestionRecord(
            dataset=dataset, data_referencia=alvo, url=url, status="error", caminho_local=None,
            tamanho_bytes=None, n_linhas=None,
            data_ingestao_utc=datetime.now(timezone.utc).isoformat(), detalhe_erro=str(e),
        )
        append_manifest(record)
        return record

    if resp.status_code == 404:
        logger.warning("Não encontrado (404) para %s/%s.", dataset, alvo)
        record = IngestionRecord(
            dataset=dataset, data_referencia=alvo, url=url, status="not_found", caminho_local=None,
            tamanho_bytes=None, n_linhas=None,
            data_ingestao_utc=datetime.now(timezone.utc).isoformat(),
        )
        append_manifest(record)
        return record

    if resp.status_code != 200:
        logger.error("Status inesperado (%d) para %s/%s", resp.status_code, dataset, alvo)
        record = IngestionRecord(
            dataset=dataset, data_referencia=alvo, url=url, status="error", caminho_local=None,
            tamanho_bytes=None, n_linhas=None,
            data_ingestao_utc=datetime.now(timezone.utc).isoformat(),
            detalhe_erro=f"status_code={resp.status_code}",
        )
        append_manifest(record)
        return record

    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(resp.content)
    tamanho = caminho.stat().st_size
    n_linhas = count_lines(caminho)
    logger.info("Salvo em %s (%.2f MB, %d linhas)", caminho, tamanho / 1e6, n_linhas)

    record = IngestionRecord(
        dataset=dataset, data_referencia=alvo, url=url, status="success",
        caminho_local=str(caminho), tamanho_bytes=tamanho, n_linhas=n_linhas,
        data_ingestao_utc=datetime.now(timezone.utc).isoformat(),
    )
    append_manifest(record)
    return record


if __name__ == "__main__":
    alvo_data = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today() - timedelta(days=5)
    alvo_dataset = sys.argv[2] if len(sys.argv) > 2 else DATASET_ITEM
    resultado = download_bulk_csv(alvo_data, dataset=alvo_dataset)
    print(resultado)
