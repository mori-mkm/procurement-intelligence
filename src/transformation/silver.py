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
import re
import unicodedata

import numpy as np
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

# Curadoria de categorias relevantes para procurement corporativo (ADR-0009).
# Validado em 2 dias de amostra + arquivo anual 2025 completo via DuckDB:
# ~2.3-2.6% do volume, consistente nas tres medicoes (108.534 de 4.736.611
# registros em 2025). Lista viva -- corrigida uma vez por falso positivo
# (termos ambiguos como "monitor"/"servidor"/"rede" isolados) e uma vez por
# falso negativo (acentuacao). Ver ADR-0009 para o historico completo.
CATEGORIAS_RELEVANTES = {
    "TI / Informatica": [
        "computador", "notebook", "software", "licenciamento de uso",
        "servidor de rede", "impressora", "monitor computador",
        "monitor de video", "storage", "firewall", "antivirus", "roteador",
    ],
    "Telecom": ["telefonia", "link dedicado", "dados moveis", "central telefonica"],
    "Consultoria / Servicos Profissionais": [
        "consultoria", "auditoria", "assessoria juridica", "advocaticio",
    ],
    "Seguranca / Vigilancia": [
        "vigilancia patrimonial", "seguranca patrimonial",
        "monitoramento eletronico", "cftv", "sistema de alarme",
    ],
    "Limpeza / Facilities": [
        "servico de limpeza", "conservacao predial", "jardinagem",
        "dedetizacao", "manutencao predial",
    ],
    "Mobiliario / Material de Escritorio": [
        "mobiliario", "cadeira escritorio", "mesa escritorio",
        "papel a4", "material de escritorio",
    ],
    "Locacao de Veiculos": [
        "locacao de veiculo", "locacao veicular", "aluguel de veiculo",
        "locacao de frota",
    ],
    "Marketing / Publicidade": ["publicidade", "propaganda", "material grafico"],
}


def _strip_accents(texto) -> str:
    if pd.isna(texto):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _compile_category_pattern(palavras: list[str]) -> re.Pattern:
    escapadas = [re.escape(p) for p in palavras]
    return re.compile(r"\b(?:" + "|".join(escapadas) + r")\b", flags=re.IGNORECASE)


def classify_relevant_category(
    df: pd.DataFrame,
    desc_col: str = "descricao_resumida",
    categorias: dict[str, list[str]] = CATEGORIAS_RELEVANTES,
) -> pd.DataFrame:
    """Classifica cada linha por categoria de produto/servico relevante para
    procurement corporativo (ADR-0009), sem remover nenhuma linha.

    Mesmo padrao de unit_flag (ADR-0005/0006): nao filtra, so anota. Quem
    consumir o Silver decide se usa is_categoria_relevante para recortar.

    Adiciona:
    - categoria_relevante: nome da primeira categoria cujo padrao bateu
      (ordem de CATEGORIAS_RELEVANTES), ou None se nenhuma bateu.
    - is_categoria_relevante: bool, True se categoria_relevante nao e None.
    """
    df = df.copy()
    desc_sem_acento = df[desc_col].apply(_strip_accents)

    categoria_atribuida = pd.Series([None] * len(df), index=df.index, dtype="object")
    ainda_sem_categoria = pd.Series(True, index=df.index)

    for nome_categoria, palavras in categorias.items():
        padrao = _compile_category_pattern(palavras)
        mask = ainda_sem_categoria & desc_sem_acento.str.contains(padrao)
        categoria_atribuida.loc[mask] = nome_categoria
        ainda_sem_categoria = ainda_sem_categoria & ~mask

    df["categoria_relevante"] = categoria_atribuida
    df["is_categoria_relevante"] = df["categoria_relevante"].notna()
    return df


def summarize_relevant_categories(df: pd.DataFrame) -> dict[str, Any]:
    """Distribuicao de categoria_relevante -- diagnostico de cobertura."""
    total = len(df)
    contagem = df["categoria_relevante"].value_counts(dropna=True)
    return {
        "total_linhas": total,
        "n_categorizado": int(df["is_categoria_relevante"].sum()),
        "pct_categorizado": round(100 * df["is_categoria_relevante"].mean(), 2),
        "por_categoria": {k: int(v) for k, v in contagem.items()},
    }

def flag_conflicting_results(
    df: pd.DataFrame,
    key_cols: list[str] = CHAVE_COMPOSTA,
    date_col: str = "data_resultado",
    value_col: str = "valor_unitario_resultado",
) -> pd.DataFrame:
    """Marca linhas cujo grupo da chave composta tem mesma data_resultado mas
    valor divergente (ADR-0010, caso RIO NEGRO) — reprocessamento em lote na
    fonte que gerou dois registros de resultado homologado para o mesmo
    item/fornecedor, sem cancelar o anterior. Nenhuma linha e removida.

    Uso recomendado por consumidor:
    - Spend Analytics (soma de valor): EXCLUIR (ver compute_spend_total) —
      senao conta o mesmo gasto duas vezes.
    - Price Benchmarking (dispersao/preco esperado): MANTER — mais um ponto
      de preco observado nao prejudica a analise.
    """
    df = df.copy()
    faltando = [c for c in key_cols + [date_col, value_col] if c not in df.columns]
    if faltando:
        df["resultado_conflitante"] = False
        return df

    n_datas = df.groupby(key_cols)[date_col].transform("nunique")
    n_valores = df.groupby(key_cols)[value_col].transform("nunique")
    df["resultado_conflitante"] = (n_datas == 1) & (n_valores > 1)
    return df

def compute_spend_total(
    df: pd.DataFrame,
    value_col: str = "valor_total_resultado",
    conflitante_col: str = "resultado_conflitante",
) -> dict[str, Any]:
    """Spend total para uso em Spend Analytics — exclui linhas
    resultado_conflitante=True para evitar contagem dupla (ADR-0010)."""
    if conflitante_col not in df.columns:
        return {"erro": f"coluna '{conflitante_col}' nao encontrada — rode flag_conflicting_results antes"}

    total_bruto = df[value_col].sum()
    df_limpo = df[~df[conflitante_col]]
    total_liquido = df_limpo[value_col].sum()
    n_excluidas = int(df[conflitante_col].sum())

    return {
        "spend_total_bruto": round(float(total_bruto), 2),
        "spend_total_liquido_sem_conflitos": round(float(total_liquido), 2),
        "valor_excluido_por_conflito": round(float(total_bruto - total_liquido), 2),
        "n_linhas_excluidas": n_excluidas,
        "pct_linhas_excluidas": round(100 * n_excluidas / len(df), 4) if len(df) else 0.0,
    }

def normalize_unit_text(unit) -> str | None:
    """Normaliza formatação de unidade_medida: remove espaços extras
    (líder/fim/duplicados internos) e padroniza caixa. NÃO interpreta
    conteúdo — não unifica abreviações como UN/UNIDADE, isso é decisão
    semântica separada. Só remove ruído de formatação que faz o mesmo
    valor parecer heterogêneo (ex: 'Unidade' vs 'Unidade  ')."""
    if pd.isna(unit):
        return unit
    texto = re.sub(r"\s+", " ", str(unit).strip())
    return texto.upper()

_BARE_UNIT_MAP = {
    "QUILOGRAMA": ("PESO", 1000.0),
    "GRAMA": ("PESO", 1.0),
    "LITRO": ("VOLUME", 1000.0),
    "MILILITRO": ("VOLUME", 1.0),
    "METRO": ("COMPRIMENTO", 1.0),
    "UNIDADE": ("CONTAGEM", None),
    "UN": ("CONTAGEM", None),
}

_QTY_UNIT_PATTERN = re.compile(r"(\d+(?:,\d+)?)\s*(KG|GR|ML|L|G)\b")

_UNIT_TO_DIMENSAO = {
    "KG": ("PESO", 1000.0),
    "GR": ("PESO", 1.0),
    "G": ("PESO", 1.0),
    "ML": ("VOLUME", 1.0),
    "L": ("VOLUME", 1000.0),
}


def parse_unit_canonical(unit_text) -> tuple[str, float | None] | None:
    """Extrai (dimensão física, valor canônico) de um texto de unidade,
    quando o número já vem embutido no texto (ex: 'EMBALAGEM 500,00 G').

    Dimensões: PESO (canonizado em gramas), VOLUME (canonizado em ML),
    CONTAGEM (sem grandeza física — 'unidade' não tem peso/volume fixo,
    por isso valor canônico é None). Retorna None se não for parseável —
    nesse caso o item cai em unit_unknown, nunca em conversão arriscada.
    """
    if pd.isna(unit_text):
        return None
    texto = str(unit_text).strip().upper()

    match = _QTY_UNIT_PATTERN.search(texto)
    if match:
        qty_str, codigo = match.groups()
        qty = float(qty_str.replace(",", "."))
        dimensao, fator = _UNIT_TO_DIMENSAO[codigo]
        return dimensao, qty * fator

    if texto in _BARE_UNIT_MAP:
        return _BARE_UNIT_MAP[texto]

    return None


def classify_unit_comparability(
    df: pd.DataFrame, item_col: str = "descricao_resumida", unit_col: str = "unidade_medida"
) -> pd.DataFrame:
    """Classifica cada linha conforme ADR-0005/0006, sem remover nada:

    - unit_comparable: item tem uma única unidade observada.
    - unit_requires_conversion: múltiplas unidades, mas todas na mesma
      dimensão física com valor canônico extraível (conversão mecânica,
      via parse_unit_canonical — não é curadoria manual).
    - unit_unknown: dimensões incompatíveis (ex: PESO vs CONTAGEM) ou
      unidade não reconhecida pelo parser. Inclui, por ora, o caso
      UN/UNIDADE (mesma dimensão CONTAGEM, mas sem valor canônico — fica
      pendente até termos uma etapa própria de normalização de abreviação).
    """
    df = df.copy()
    df[unit_col] = df[unit_col].apply(normalize_unit_text)

    parsed = df[unit_col].apply(parse_unit_canonical)
    df["_dimensao_fisica"] = parsed.apply(lambda x: x[0] if x else None)

    n_unidades_por_item = df.groupby(item_col)[unit_col].transform("nunique")
    n_dimensoes_por_item = df.groupby(item_col)["_dimensao_fisica"].transform("nunique")
    tem_nao_parseavel = df.groupby(item_col)["_dimensao_fisica"].transform(lambda s: s.isna().any())

    condicoes = [
        n_unidades_por_item <= 1,
        (n_dimensoes_por_item == 1) & (~tem_nao_parseavel),
    ]
    escolhas = ["unit_comparable", "unit_requires_conversion"]
    df["unit_flag"] = np.select(condicoes, escolhas, default="unit_unknown")

    return df.drop(columns=["_dimensao_fisica"])


def summarize_unit_flags(df: pd.DataFrame) -> dict[str, Any]:
    """Distribuição das três flags — diagnóstico de quanto o parser
    resolveu automaticamente vs. quanto ficou sem solução."""
    contagem = df["unit_flag"].value_counts()
    total = len(df)
    return {
        flag: {"n": int(contagem.get(flag, 0)), "pct": round(100 * contagem.get(flag, 0) / total, 2)}
        for flag in ["unit_comparable", "unit_requires_conversion", "unit_unknown"]
    }

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
    df_categorizado = classify_relevant_category(df_resolvido)
    df_final = flag_conflicting_results(df_categorizado)

    dist_fornecedores = suppliers_per_item_distribution(df_final)
    validacao_chave = validate_composite_key(df_final)
    caracterizacao_violacoes = characterize_key_violations(df_final)
    resumo_categorias = summarize_relevant_categories(df_final)
    resumo_spend = compute_spend_total(df_final)

    relatorio = {
        "deduplicacao": stats_dedup,
        "resolucao_revisoes_temporais": stats_resolucao,
        "distribuicao_fornecedores_por_item": dist_fornecedores,
        "validacao_chave_composta": validacao_chave,
        "caracterizacao_violacoes": caracterizacao_violacoes,
        "categorias_relevantes": resumo_categorias,
        "resultado_conflitante": {
            "n_linhas_flagadas": int(df_final["resultado_conflitante"].sum()),
            "pct_linhas_flagadas": round(100 * df_final["resultado_conflitante"].mean(), 4),
        },
        "spend_total": resumo_spend,
    }
    return relatorio, df_final


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