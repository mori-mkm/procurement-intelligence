"""
Funções de perfilagem de qualidade para a camada Bronze.
Bronze não é alterado por essas funções — elas apenas leem e relatam.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

# Campos de identificador com risco real de corrupção por inferência numérica
# automática: CNPJ (zero à esquerda) e chaves longas tipo surrogate key
# (perda de precisão em float64 acima de ~15-17 dígitos significativos).
ID_COLUMNS = [
    "id_compra", "id_compra_item", "cod_compra", "cod_item_compra",
    "cod_fornecedor", "cod_item_catalogo", "orgao_entidade_cnpj",
    "ID_contratacao_PNCP", "numero_controle_PNCP_compra", "srk_pncp_item_compra",
    "COD_RESULTADO_ITEM",
    # novos (dataset de cabeçalho, VW_FT_PNCP_COMPRA)
    "orgao_subrogado_cnpj", "codigo_orgao",
    "unidade_orgao_codigo_unidade", "unidade_orgao_codigo_ibge",
    "unidade_subrogada_codigo_unidade", "unidade_subrogada_codigo_ibge",
    "numero_controle_PNCP", "codigo_modalidade", "codigo_modo_disputa",
]

def load_bronze_csv(path: Path) -> pd.DataFrame:
    """Lê o CSV bruto de Bronze exatamente como está.

    IDs/códigos (ID_COLUMNS) são forçados como string na leitura — sem isso,
    o pandas infere alguns como float64, o que corrompe CNPJ com zero à
    esquerda e arrisca perda de precisão em chaves longas. A correção
    precisa acontecer aqui, na leitura: depois de virar float, a
    representação original já foi perdida.
    """
    cabecalho = pd.read_csv(path, sep=",", encoding="utf-8", nrows=0)
    dtype_overrides = {col: str for col in ID_COLUMNS if col in cabecalho.columns}
    return pd.read_csv(path, sep=",", encoding="utf-8", low_memory=False, dtype=dtype_overrides)


def basic_shape(df: pd.DataFrame) -> dict[str, Any]:
    return {"n_linhas": len(df), "n_colunas": df.shape[1], "colunas": list(df.columns)}


def null_profile(df: pd.DataFrame) -> pd.DataFrame:
    perfil = pd.DataFrame({
        "n_nulos": df.isna().sum(),
        "pct_nulos": (df.isna().mean() * 100).round(2),
        "dtype_inferido": df.dtypes.astype(str),
    })
    return perfil.sort_values("pct_nulos", ascending=False)


def exact_duplicates(df: pd.DataFrame) -> dict[str, Any]:
    n_dup = int(df.duplicated().sum())
    return {"n_duplicatas_exatas": n_dup, "pct_duplicatas_exatas": round(100 * n_dup / len(df), 4)}


def key_duplicates(df: pd.DataFrame, key_col: str = "id_compra_item") -> dict[str, Any]:
    if key_col not in df.columns:
        return {"erro": f"coluna '{key_col}' não encontrada"}
    n_dup = int(df[key_col].duplicated().sum())
    return {"coluna_chave": key_col, "n_duplicados": n_dup, "pct_duplicados": round(100 * n_dup / len(df), 4)}


def invalid_dates(df: pd.DataFrame, date_cols: list[str]) -> dict[str, dict]:
    resultado = {}
    for col in date_cols:
        if col not in df.columns:
            resultado[col] = {"erro": "coluna não encontrada"}
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        n_invalido = int(max(parsed.isna().sum() - df[col].isna().sum(), 0))
        resultado[col] = {
            "n_invalido": n_invalido,
            "pct_invalido": round(100 * n_invalido / len(df), 4),
            "min_valido": str(parsed.min()),
            "max_valido": str(parsed.max()),
        }
    return resultado


def value_range_check(df: pd.DataFrame, col: str, min_allowed: float = 0) -> dict[str, Any]:
    if col not in df.columns:
        return {"erro": f"coluna '{col}' não encontrada"}
    valores = pd.to_numeric(df[col], errors="coerce")
    abaixo = int((valores < min_allowed).sum())
    zero = int((valores == 0).sum())
    return {
        "coluna": col,
        f"n_abaixo_de_{min_allowed}": abaixo,
        f"pct_abaixo_de_{min_allowed}": round(100 * abaixo / len(df), 4),
        "n_igual_a_zero": zero,
        "pct_igual_a_zero": round(100 * zero / len(df), 4),
    }


def missing_reference_check(df: pd.DataFrame, col: str) -> dict[str, Any]:
    if col not in df.columns:
        return {"erro": f"coluna '{col}' não encontrada"}
    n_null = int(df[col].isna().sum())
    return {"coluna": col, "n_ausente": n_null, "pct_ausente": round(100 * n_null / len(df), 4)}


def unit_heterogeneity(df: pd.DataFrame, item_col: str, unit_col: str) -> dict[str, Any]:
    if item_col not in df.columns or unit_col not in df.columns:
        return {"erro": f"coluna(s) não encontrada(s): {item_col}, {unit_col}"}
    validos = df[df[item_col].notna()]
    if validos.empty:
        return {"aviso": "nenhum registro com item preenchido"}
    contagem = validos.groupby(item_col)[unit_col].nunique()
    n_multi = int((contagem > 1).sum())
    return {
        "n_itens_distintos": int(len(contagem)),
        "n_itens_com_multiplas_unidades": n_multi,
        "pct_itens_com_multiplas_unidades": round(100 * n_multi / len(contagem), 2),
    }

def list_multi_unit_items(
    df: pd.DataFrame,
    item_col: str = "descricao_resumida",
    unit_col: str = "unidade_medida",
    catmat_col: str = "cod_item_catalogo",
    top_n: int = 30,
) -> list[dict]:
    """Lista itens com mais de uma unidade de medida observada, ordenados por
    volume de transações (não alfabeticamente) — para priorizar curadoria de
    conversão pelo que representa mais spend, não pelo que aparece primeiro.

    n_catmats_distintos ajuda a diferenciar: múltiplas unidades + único
    CATMAT sugere mesmo produto em embalagens diferentes (candidato real a
    conversão); múltiplas unidades + múltiplos CATMATs sugere produtos
    diferentes disfarçados de item único pela descrição genérica (problema
    de normalização de texto, não de unidade).

    Não decide nada — só lista para inspeção manual, conforme ADR-0005.
    """
    if item_col not in df.columns or unit_col not in df.columns:
        return []

    resultado = []
    for nome_item, grupo in df.groupby(item_col):
        unidades = grupo[unit_col].dropna().unique()
        if len(unidades) > 1:
            entrada = {
                "item": nome_item,
                "n_transacoes": len(grupo),
                "n_unidades_distintas": len(unidades),
                "unidades": sorted(str(u) for u in unidades),
                "n_catmats_distintos": (
                    int(grupo[catmat_col].nunique()) if catmat_col in grupo.columns else None
                ),
            }
            resultado.append(entrada)

    resultado.sort(key=lambda x: x["n_transacoes"], reverse=True)
    return resultado[:top_n]

def load_reference_schema(path: Path = Path("src/quality/reference_schema.json")) -> list[str]:
    """Carrega o schema de referência versionado (ADR-0008). Retorna lista vazia se não existir."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as f:
        data = json.load(f)
    return data.get("colunas", [])


def schema_drift_check(df: pd.DataFrame, reference_columns: list[str]) -> dict[str, Any]:
    """Compara colunas do arquivo do dia contra o schema de referência. Não modifica df."""
    colunas_atuais = list(df.columns)
    novas = sorted(set(colunas_atuais) - set(reference_columns))
    ausentes = sorted(set(reference_columns) - set(colunas_atuais))
    return {
        "schema_bate": len(novas) == 0 and len(ausentes) == 0,
        "colunas_novas": novas,
        "colunas_ausentes": ausentes,
        "n_colunas_atual": len(colunas_atuais),
        "n_colunas_referencia": len(reference_columns),
    }

def build_bronze_quality_report(df: pd.DataFrame, reference_columns: list[str] | None = None) -> dict[str, Any]:
    """Relatório completo de qualidade da Etapa 2 (Bronze validation)."""
    if reference_columns is None:
        reference_columns = load_reference_schema()

    relatorio = {
        "shape": basic_shape(df),
        "duplicatas_exatas": exact_duplicates(df),
        "duplicatas_id_compra_item": key_duplicates(df, "id_compra_item"),
        "datas_invalidas": invalid_dates(df, ["data_inclusao_pncp", "data_atualizacao_pncp", "data_resultado"]),
        "valor_unitario_resultado": value_range_check(df, "valor_unitario_resultado"),
        "valor_unitario_estimado": value_range_check(df, "valor_unitario_estimado"),
        "quantidade": value_range_check(df, "quantidade"),
        "quantidade_resultado": value_range_check(df, "quantidade_resultado"),
        "fornecedor_ausente": missing_reference_check(df, "cod_fornecedor"),
        "catmat_ausente": missing_reference_check(df, "cod_item_catalogo"),
        "heterogeneidade_unidade_por_catmat": unit_heterogeneity(df, "cod_item_catalogo", "unidade_medida"),
    }

    if reference_columns:
        relatorio["schema_drift"] = schema_drift_check(df, reference_columns)
    else:
        relatorio["schema_drift"] = {"aviso": "schema de referência não encontrado — checagem pulada"}

    return relatorio

if __name__ == "__main__":
    alvo_data = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    ano, mes, dia = alvo_data.strftime("%Y"), alvo_data.strftime("%m"), alvo_data.strftime("%d")
    caminho = (
        Path("data/bronze/pncp_compra_item")
        / f"dt={ano}-{mes}-{dia}"
        / f"comprasGOV-diario-VW_FT_PNCP_COMPRA_ITEM-{ano}-{mes}-{dia}.csv"
    )

    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        print("Rode a ingestão para essa data primeiro: python -m src.ingestion.pncp_bulk", alvo_data.isoformat())
        sys.exit(1)

    print(f"Carregando {caminho} ...")
    df = load_bronze_csv(caminho)
    relatorio = build_bronze_quality_report(df)
    print(json.dumps(relatorio, ensure_ascii=False, indent=2, default=str))