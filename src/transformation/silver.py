"""
Transformação Bronze -> Silver.
Tipagem explícita, deduplicação (ADR-0004) e validação da chave composta.
Não filtra nem remove nenhum caso "ruim" silenciosamente — só relata.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from typing import Any

import pandas as pd

from src.ingestion.pncp_bulk import local_path_for
from src.quality.checks import load_bronze_csv

# Colunas que identificam a linha em si (não o conteúdo de negócio) e por
# isso não devem participar da deduplicação exata — comparar por elas
# nunca converge, porque cada linha tem um valor próprio por definição.
# COD_RESULTADO_ITEM confirmado como caso real em 22/05/2026: duas linhas
# com conteúdo de negócio idêntico, diferindo só nesse campo.
COLUNAS_IGNORAR_NA_DEDUP = ["COD_RESULTADO_ITEM", "srk_pncp_item_compra"]

COLUNAS_MONETARIAS = [
    "valor_unitario_estimado", "valor_total", "valor_total_resultado", "valor_unitario_resultado",
]
COLUNAS_QUANTIDADE = ["quantidade", "quantidade_resultado"]
COLUNAS_DATA = ["data_inclusao_pncp", "data_atualizacao_pncp", "data_resultado"]

CHAVE_COMPOSTA = ["id_compra_item", "cod_fornecedor"]


def apply_typing(df: pd.DataFrame) -> pd.DataFrame:
    """Tipagem explícita de valores monetários, quantidades e datas.
    IDs já vêm como string de load_bronze_csv — não mexe neles aqui.
    Não remove nem filtra nenhuma linha."""
    df = df.copy()
    for col in COLUNAS_MONETARIAS + COLUNAS_QUANTIDADE:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in COLUNAS_DATA:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def remove_exact_duplicates(
    df: pd.DataFrame, ignore_cols: list[str] = COLUNAS_IGNORAR_NA_DEDUP
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """ADR-0004, passo 1: remove linhas exatamente idênticas em todas as
    colunas de conteúdo de negócio. Colunas de identificação de linha
    (ignore_cols) são excluídas da comparação, mas preservadas no resultado —
    ficam com o valor da primeira ocorrência de cada grupo duplicado."""
    n_antes = len(df)
    colunas_comparacao = [c for c in df.columns if c not in ignore_cols]
    df_dedup = df.drop_duplicates(subset=colunas_comparacao, keep="first").reset_index(drop=True)
    n_depois = len(df_dedup)
    stats = {
        "linhas_antes": n_antes,
        "linhas_depois": n_depois,
        "duplicatas_removidas": n_antes - n_depois,
        "pct_duplicatas_removidas": round(100 * (n_antes - n_depois) / n_antes, 4) if n_antes else 0.0,
        "colunas_ignoradas_na_comparacao": [c for c in ignore_cols if c in df.columns],
    }
    return df_dedup, stats

def resolve_temporal_revisions(
    df: pd.DataFrame, key_cols: list[str] = CHAVE_COMPOSTA, date_col: str = "data_resultado"
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Para grupos da chave composta com múltiplas datas de resultado
    distintas, mantém só a linha com data_resultado mais recente (revisão
    histórica). Grupos onde todas as linhas têm a mesma data (conflito sem
    critério de desempate, ex: RIO NEGRO em 22/05/2026) não são alterados
    aqui — continuam com todas as linhas, e devem aparecer como violação em
    validate_composite_key. Essa função não decide qual valor está certo
    nesse segundo caso, só resolve o caso onde a data já dá o critério."""
    if date_col not in df.columns or not all(c in df.columns for c in key_cols):
        return df, {"erro": f"coluna(s) não encontrada(s): {key_cols + [date_col]}"}

    n_antes = len(df)

    n_datas_por_grupo = df.groupby(key_cols)[date_col].transform("nunique")
    grupos_multi_data = n_datas_por_grupo > 1

    df_grupos_unica_data = df[~grupos_multi_data]
    df_grupos_multi_data = df[grupos_multi_data]

    if not df_grupos_multi_data.empty:
        df_multi_data_resolvido = (
            df_grupos_multi_data.sort_values(date_col, ascending=False)
            .drop_duplicates(subset=key_cols, keep="first")
        )
    else:
        df_multi_data_resolvido = df_grupos_multi_data

    df_resolvido = pd.concat([df_grupos_unica_data, df_multi_data_resolvido], ignore_index=True)
    n_depois = len(df_resolvido)

    stats = {
        "linhas_antes": n_antes,
        "linhas_depois": n_depois,
        "revisoes_temporais_resolvidas": n_antes - n_depois,
    }
    return df_resolvido, stats

def suppliers_per_item_distribution(
    df: pd.DataFrame, item_col: str = "id_compra_item", supplier_col: str = "cod_fornecedor"
) -> dict[str, Any]:
    """Fornecedores distintos por id_compra_item, medido após a deduplicação exata."""
    if item_col not in df.columns or supplier_col not in df.columns:
        return {"erro": f"coluna(s) não encontrada(s): {item_col}, {supplier_col}"}
    contagem = df.groupby(item_col)[supplier_col].nunique()
    return {
        "n_itens_distintos": int(len(contagem)),
        "n_itens_com_multiplos_fornecedores": int((contagem > 1).sum()),
        "pct_itens_com_multiplos_fornecedores": round(100 * (contagem > 1).mean(), 2),
        "distribuicao_n_fornecedores": {int(k): int(v) for k, v in contagem.value_counts().sort_index().items()},
    }


def validate_composite_key(df: pd.DataFrame, key_cols: list[str] = CHAVE_COMPOSTA) -> dict[str, Any]:
    """Verifica se a chave composta do ADR-0004 é única após a deduplicação exata.

    Não corrige nada automaticamente. Se houver violação, retorna uma amostra
    dos casos para investigação manual, não uma solução pronta.
    """
    faltando = [c for c in key_cols if c not in df.columns]
    if faltando:
        return {"erro": f"coluna(s) não encontrada(s): {faltando}"}

    n_total = len(df)
    duplicados_mask = df.duplicated(subset=key_cols, keep=False)
    n_violacoes = int(df.duplicated(subset=key_cols, keep="first").sum())

    resultado: dict[str, Any] = {
        "chave": key_cols,
        "chave_e_unica": n_violacoes == 0,
        "n_linhas_totais": n_total,
        "n_violacoes": n_violacoes,
        "pct_violacoes": round(100 * n_violacoes / n_total, 4) if n_total else 0.0,
    }

    if n_violacoes > 0:
        colunas_diagnostico = [
            c for c in key_cols + ["nome_fornecedor", "valor_unitario_resultado", "quantidade_resultado", "data_resultado"]
            if c in df.columns
        ]
        amostra = df.loc[duplicados_mask, colunas_diagnostico].sort_values(key_cols).head(20)
        resultado["amostra_casos_problematicos"] = amostra.to_dict(orient="records")

    return resultado

def characterize_key_violations(
    df: pd.DataFrame,
    key_cols: list[str] = CHAVE_COMPOSTA,
    value_col: str = "valor_unitario_resultado",
    date_col: str = "data_resultado",
    compra_col: str = "id_compra",
) -> dict[str, Any]:
    """Caracteriza as violações da chave composta: revisão temporal legítima
    (datas diferentes) vs. duplicata no mesmo dia (mesma data, valor igual
    ou divergente). Não corrige nada, só descreve."""
    faltando = [c for c in key_cols + [value_col, date_col] if c not in df.columns]
    if faltando:
        return {"erro": f"coluna(s) não encontrada(s): {faltando}"}

    grupos = df[df.duplicated(subset=key_cols, keep=False)].groupby(key_cols)

    mesma_data_mesmo_valor = 0
    mesma_data_valor_diferente = 0
    data_diferente_mesmo_valor = 0
    data_diferente_valor_diferente = 0

    for _, grupo in grupos:
        n_datas = grupo[date_col].nunique()
        n_valores = grupo[value_col].nunique()
        if n_datas == 1 and n_valores == 1:
            mesma_data_mesmo_valor += 1
        elif n_datas == 1 and n_valores > 1:
            mesma_data_valor_diferente += 1
        elif n_datas > 1 and n_valores == 1:
            data_diferente_mesmo_valor += 1
        else:
            data_diferente_valor_diferente += 1

    resultado = {
        "n_grupos_duplicados": grupos.ngroups,
        "mesma_data_mesmo_valor": mesma_data_mesmo_valor,
        "mesma_data_valor_diferente": mesma_data_valor_diferente,
        "data_diferente_mesmo_valor": data_diferente_mesmo_valor,
        "data_diferente_valor_diferente": data_diferente_valor_diferente,
    }

    if compra_col in df.columns:
        compras_envolvidas = df.loc[df.duplicated(subset=key_cols, keep=False), compra_col]
        contagem_por_compra = compras_envolvidas.value_counts()
        resultado["n_compras_distintas_envolvidas"] = int(len(contagem_por_compra))
        resultado["top_5_compras_por_n_linhas_envolvidas"] = contagem_por_compra.head(5).to_dict()

    return resultado

def build_silver_transformation_report(df_bronze: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    df_tipado = apply_typing(df_bronze)
    df_dedup, stats_dedup = remove_exact_duplicates(df_tipado)
    df_resolvido, stats_resolucao = resolve_temporal_revisions(df_dedup)

    dist_fornecedores = suppliers_per_item_distribution(df_resolvido)
    validacao_chave = validate_composite_key(df_resolvido)
    caracterizacao_violacoes = characterize_key_violations(df_resolvido)

    relatorio = {
        "deduplicacao": stats_dedup,
        "resolucao_revisoes_temporais": stats_resolucao,
        "distribuicao_fornecedores_por_item": dist_fornecedores,
        "validacao_chave_composta": validacao_chave,
        "caracterizacao_violacoes": caracterizacao_violacoes,
    }
    return relatorio, df_resolvido


if __name__ == "__main__":
    alvo_data = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    caminho = local_path_for(alvo_data)

    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        print("Rode a ingestão para essa data primeiro: python -m src.ingestion.pncp_bulk", alvo_data.isoformat())
        sys.exit(1)

    print(f"Carregando {caminho} ...")
    df_bronze = load_bronze_csv(caminho)
    relatorio, df_silver = build_silver_transformation_report(df_bronze)
    print(json.dumps(relatorio, ensure_ascii=False, indent=2, default=str))