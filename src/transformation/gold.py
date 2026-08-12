"""
Transformação Silver -> Gold: modelo dimensional.
Fase 4. Ver docs/adr/ para decisões de grão, chaves e limitações conhecidas.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

# Campos do cabeçalho (VW_FT_PNCP_COMPRA) que compõem dim_buyer.
# orgao_subrogado_* NÃO é usado: investigação (Fase 4) mostrou que, nos
# casos observados, é sempre a mesma entidade que orgao_entidade_*, apenas
# com o CNPJ mal tipado na fonte (perda de zero à esquerda). Não há
# evidência de sub-rogação real (compra em nome de terceiro) nos dados
# analisados até aqui.
COLUNAS_DIM_BUYER = [
    "id_compra",
    "orgao_entidade_cnpj",
    "orgao_entidade_razao_social",
    "unidade_orgao_uf_sigla",
    "unidade_orgao_municipio_nome",
    "codigo_modalidade",
    "modalidade_nome",
]


def build_dim_buyer(df_cabecalho: pd.DataFrame) -> pd.DataFrame:
    """Constrói dim_buyer a partir do Bronze de cabeçalho (VW_FT_PNCP_COMPRA),
    já carregado via load_bronze_csv (tipagem de ID já resolvida).

    Grão: 1 linha por id_compra. Não deduplica nem valida aqui — isso é
    responsabilidade de quem ingeriu (id_compra já confirmado único na
    investigação da Fase 4, mas não assumimos isso silenciosamente para
    sempre; ver validate_dim_buyer_grain).
    """
    colunas_disponiveis = [c for c in COLUNAS_DIM_BUYER if c in df_cabecalho.columns]
    faltando = set(COLUNAS_DIM_BUYER) - set(colunas_disponiveis)
    if faltando:
        raise ValueError(f"Colunas esperadas ausentes no cabeçalho: {faltando}")

    return df_cabecalho[colunas_disponiveis].copy()


def validate_dim_buyer_grain(dim_buyer: pd.DataFrame) -> dict[str, Any]:
    """Confirma que id_compra é único em dim_buyer — não assume, mede."""
    n_total = len(dim_buyer)
    n_duplicado = int(dim_buyer["id_compra"].duplicated().sum())
    return {
        "n_linhas": n_total,
        "id_compra_duplicado": n_duplicado,
        "grao_valido": n_duplicado == 0,
    }


def join_fact_with_buyer(df_fact_item: pd.DataFrame, dim_buyer: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Junta o Silver de item (grão id_compra_item x cod_fornecedor) com
    dim_buyer (grão id_compra) via id_compra. Left join -- preserva todas
    as linhas de item mesmo se o cabeçalho correspondente não tiver sido
    ingerido (caso esperado: cobertura de cabeçalho pode ser menor que a
    de item, já que ingerimos os dois separadamente).
    """
    if "id_compra" not in df_fact_item.columns:
        raise ValueError("df_fact_item precisa ter a coluna id_compra para o join")

    n_antes = len(df_fact_item)
    resultado = df_fact_item.merge(
        dim_buyer, on="id_compra", how="left", suffixes=("", "_buyer")
    )
    n_depois = len(resultado)

    n_sem_match = int(resultado["unidade_orgao_uf_sigla"].isna().sum())

    stats = {
        "linhas_fact_antes": n_antes,
        "linhas_apos_join": n_depois,
        "linhas_sem_match_no_buyer": n_sem_match,
        "pct_sem_match": round(100 * n_sem_match / n_antes, 4) if n_antes else 0.0,
    }

    if n_depois != n_antes:
        stats["aviso"] = "Join alterou contagem de linhas — dim_buyer pode ter id_compra duplicado. Investigar antes de confiar no resultado."

    return resultado, stats


def resolve_duplicate_buyer_records(
    df_cabecalho: pd.DataFrame, date_col: str = "data_publicacao_pncp"
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Resolve id_compra duplicado no cabeçalho combinado multi-ano.

    Dois fenômenos observados (Fase 4, investigação real): (1) duplicata
    dentro do mesmo arquivo anual, causa não identificada com certeza,
    concentrada em 2024; (2) sobreposição entre arquivos anuais adjacentes
    (compra publicada perto da virada do ano aparece nos dois snapshots).

    Critério: mantém a linha com data_publicacao_pncp mais recente por
    id_compra. Não é o critério ideal (não temos data_atualizacao_pncp
    populada nos casos observados para desempate mais preciso), mas é o
    único campo disponível e consistentemente preenchido nos casos vistos.
    """
    n_antes = len(df_cabecalho)
    n_ids_distintos_antes = df_cabecalho["id_compra"].nunique()

    df_resolvido = (
        df_cabecalho.sort_values(date_col, ascending=False)
        .drop_duplicates(subset="id_compra", keep="first")
        .reset_index(drop=True)
    )

    stats = {
        "linhas_antes": n_antes,
        "linhas_depois": len(df_resolvido),
        "duplicatas_removidas": n_antes - len(df_resolvido),
        "id_compra_distintos": n_ids_distintos_antes,
    }
    return df_resolvido, stats


def load_dim_buyer_from_annual(anos: list[int]) -> pd.DataFrame:
    """Constrói dim_buyer a partir dos Parquets anuais já materializados
    (src/ingestion/pncp_bulk_annual.py), cobrindo múltiplos anos. Resolve a
    lacuna de cobertura da Fase 4: item diário referencia id_compra de
    datas de publicação muito anteriores ao dia do snapshot de cabeçalho.

    Também resolve id_compra duplicado entre/dentro dos arquivos anuais
    (ver resolve_duplicate_buyer_records) antes de montar o dim_buyer final.
    """
    from src.ingestion.pncp_bulk_annual import local_parquet_path, DATASET_COMPRA

    frames = []
    for ano in anos:
        caminho = local_parquet_path(ano, DATASET_COMPRA)
        if not caminho.exists():
            raise FileNotFoundError(
                f"Parquet anual não encontrado para {ano}: {caminho}. "
                f"Rode: python -m src.ingestion.pncp_bulk_annual {ano} {DATASET_COMPRA}"
            )
        frames.append(pd.read_parquet(caminho))

    df_completo = pd.concat(frames, ignore_index=True)
    df_completo["data_publicacao_pncp"] = pd.to_datetime(df_completo["data_publicacao_pncp"], errors="coerce")
    df_resolvido, _ = resolve_duplicate_buyer_records(df_completo)
    return build_dim_buyer(df_resolvido)