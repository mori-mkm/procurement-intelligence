"""
Ingestão de arquivos bulk ANUAIS do PNCP/compras.gov.br via DuckDB.

Diferente de pncp_bulk.py (diário, requests.get direto): arquivos anuais
são grandes demais para baixar inteiros na memória Python. Usamos o motor
de streaming CSV do DuckDB para ler direto da URL remota e materializar
como Parquet local — mais compacto e rápido de reconsultar que o CSV bruto.

IDs são forçados como VARCHAR na leitura (não depois) — se deixarmos o
DuckDB inferir int64 primeiro, zero à esquerda já foi perdido antes de
qualquer CAST posterior conseguir recuperar.

Ver ADR-0007 (motivação) e ADR-0011 (a escrever, após validação).
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import duckdb

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

BASE_BULK = "https://repositorio.dados.gov.br/seges/comprasgov"

DATASET_COMPRA = "VW_FT_PNCP_COMPRA"
DATASET_ITEM = "VW_FT_PNCP_COMPRA_ITEM"

_FOLDER_BY_DATASET = {
    DATASET_COMPRA: "pncp_compra_anual",
    DATASET_ITEM: "pncp_compra_item_anual",
}

# Campos de ID conhecidos no cabeçalho -- forçados a VARCHAR na leitura.
# Confirmado via DESCRIBE na Fase 4 (investigação BB/Caixa e exploracao de
# cabecalho): esses campos vem int64 por padrao, corrompendo CNPJ/id_compra
# com zero a esquerda.
ID_COLUMNS_COMPRA = [
    "id_compra", "orgao_entidade_cnpj", "orgao_subrogado_cnpj", "codigo_orgao",
    "unidade_orgao_codigo_unidade", "unidade_orgao_codigo_ibge",
    "unidade_subrogada_codigo_unidade", "unidade_subrogada_codigo_ibge",
    "numero_controle_PNCP", "cod_compra",
]

BRONZE_ANNUAL_ROOT = Path("data/bronze")
MANIFEST_PATH = Path("data/bronze") / "_manifest" / "ingestion_annual_log.jsonl"


@dataclass
class AnnualIngestionRecord:
    dataset: str
    ano: int
    url: str
    status: str  # "success" | "skipped_existing" | "error"
    caminho_local: Optional[str]
    n_linhas: Optional[int]
    data_ingestao_utc: str
    detalhe_erro: Optional[str] = None


def build_annual_url(ano: int, dataset: str) -> str:
    return f"{BASE_BULK}/anual/{ano}/comprasGOV-anual-{dataset}-{ano}.csv"


def local_parquet_path(ano: int, dataset: str) -> Path:
    pasta = _FOLDER_BY_DATASET.get(dataset, dataset.lower() + "_anual")
    return BRONZE_ANNUAL_ROOT / pasta / f"ano={ano}" / f"{dataset}-{ano}.parquet"


def _build_types_clause(columns: list[str]) -> str:
    pares = ", ".join(f"'{c}': 'VARCHAR'" for c in columns)
    return "{" + pares + "}"


def append_manifest(record: AnnualIngestionRecord) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def already_ingested_annual(ano: int, dataset: str) -> bool:
    return local_parquet_path(ano, dataset).exists()


def download_annual_via_duckdb(
    ano: int, dataset: str = DATASET_COMPRA, force: bool = False,
    id_columns: list[str] | None = None,
) -> AnnualIngestionRecord:
    caminho = local_parquet_path(ano, dataset)
    url = build_annual_url(ano, dataset)

    if not force and already_ingested_annual(ano, dataset):
        logger.info("Já materializado: %s/%s (%s) — pulando.", dataset, ano, caminho)
        record = AnnualIngestionRecord(
            dataset=dataset, ano=ano, url=url, status="skipped_existing",
            caminho_local=str(caminho), n_linhas=None,
            data_ingestao_utc=datetime.now(timezone.utc).isoformat(),
        )
        append_manifest(record)
        return record

    if id_columns is None:
        id_columns = ID_COLUMNS_COMPRA if dataset == DATASET_COMPRA else []

    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    types_clause = f", types={_build_types_clause(id_columns)}" if id_columns else ""
    query = f"""
        COPY (
            SELECT * FROM read_csv_auto('{url}', ignore_errors=true{types_clause})
        ) TO '{caminho.as_posix()}' (FORMAT PARQUET)
    """

    logger.info("Materializando %s (pode levar alguns minutos)...", url)
    try:
        con.execute(query)
        n_linhas = con.execute(f"SELECT COUNT(*) FROM read_parquet('{caminho.as_posix()}')").fetchone()[0]
        logger.info("Salvo em %s (%d linhas)", caminho, n_linhas)
        record = AnnualIngestionRecord(
            dataset=dataset, ano=ano, url=url, status="success",
            caminho_local=str(caminho), n_linhas=n_linhas,
            data_ingestao_utc=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Erro ao materializar %s: %s", url, e)
        record = AnnualIngestionRecord(
            dataset=dataset, ano=ano, url=url, status="error", caminho_local=None,
            n_linhas=None, data_ingestao_utc=datetime.now(timezone.utc).isoformat(),
            detalhe_erro=str(e),
        )
    finally:
        con.close()

    append_manifest(record)
    return record


if __name__ == "__main__":
    ano_alvo = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    dataset_alvo = sys.argv[2] if len(sys.argv) > 2 else DATASET_COMPRA
    resultado = download_annual_via_duckdb(ano_alvo, dataset_alvo)
    print(resultado)