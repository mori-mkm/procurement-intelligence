"""
Modulo 1 - Spend Intelligence: spend por categoria relevante e concentracao
de fornecedor (HHI / Curva ABC). Fase 6.

Convencao de HHI: escala padrao DOJ/FTC (0-10.000), calculada como
soma dos quadrados das participacoes percentuais (0-100) de cada
fornecedor dentro do agrupamento. Classificacao de referencia:
<1.500 nao concentrado, 1.500-2.500 moderadamente concentrado,
>2.500 altamente concentrado.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

CATEGORIA_NAO_CLASSIFICADA = "Não categorizado"

HHI_LIMIAR_MODERADO = 1500
HHI_LIMIAR_ALTO = 2500


def classify_hhi(hhi: float) -> str:
    """Classificacao padrao DOJ/FTC de concentracao de mercado."""
    if pd.isna(hhi):
        return "indefinido"
    if hhi < HHI_LIMIAR_MODERADO:
        return "nao concentrado"
    if hhi < HHI_LIMIAR_ALTO:
        return "moderadamente concentrado"
    return "altamente concentrado"


def _exclude_flagged_rows(df: pd.DataFrame, flag_col: str = "is_value_outlier") -> pd.DataFrame:
    """Exclui linhas flagadas por outlier de valor (ADR-0014) E por valor
    extremo em relacao a mediana global (segunda camada, mais simples e
    robusta que o z-score por grupo -- ver flag_extreme_by_global_median)."""
    resultado = df
    if flag_col in df.columns:
        resultado = resultado[~resultado[flag_col].fillna(False)]
    extremo = flag_extreme_by_global_median(df)
    resultado = resultado[~extremo.reindex(resultado.index)]
    return resultado


def flag_extreme_by_global_median(
    df_fact: pd.DataFrame,
    value_col: str = "total_price",
    existing_outlier_col: str = "is_value_outlier",
    multiplier: float = 1000.0,
) -> pd.Series:
    """Segunda camada de seguranca, mais simples que flag_value_outliers
    (gold.py). Calcula a mediana de value_col SO entre linhas ja
    nao-flagadas (robusto contra os outliers mais obvios, que ja foram
    excluidos) e marca qualquer linha (flagada ou nao) que exceda
    `multiplier` vezes essa mediana global.

    Nao depende de item_key -- pega casos que escapam do z-score por
    grupo quando o item_key mistura contratos de escala muito diferente
    (achado real, Fase 6: "pericia, laudo e avaliacao",
    "prestacao de servicos bancarios" etc.).
    """
    ja_excluido = df_fact[existing_outlier_col].fillna(False) if existing_outlier_col in df_fact.columns else pd.Series(False, index=df_fact.index)
    mediana_global = df_fact.loc[~ja_excluido, value_col].median()
    limite = mediana_global * multiplier
    return df_fact[value_col] > limite


def compute_spend_by_category(
    df_fact: pd.DataFrame,
    category_col: str = "categoria_relevante",
    value_col: str = "total_price",
    supplier_col: str = "supplier_key",
    item_col: str = "item_key",
) -> pd.DataFrame:
    """Spend total, numero de transacoes, fornecedores e itens distintos
    por categoria_relevante (ADR-0009). Linhas sem categoria (maioria do
    volume, ver ADR-0009) sao agrupadas em CATEGORIA_NAO_CLASSIFICADA,
    nao descartadas -- preserva o contexto de quanto do universo total
    as categorias curadas realmente representam."""
    df = _exclude_flagged_rows(df_fact.copy())
    df[category_col] = df[category_col].fillna(CATEGORIA_NAO_CLASSIFICADA)

    agg = df.groupby(category_col).agg(
        spend_total=(value_col, "sum"),
        n_transacoes=(value_col, "size"),
        n_fornecedores_distintos=(supplier_col, "nunique"),
        n_itens_distintos=(item_col, "nunique"),
    )

    spend_universo_total = df[value_col].sum()
    agg["pct_do_spend_total"] = round(100 * agg["spend_total"] / spend_universo_total, 4)

    return agg.reset_index().sort_values("spend_total", ascending=False).reset_index(drop=True)


def _supplier_spend_shares(
    df_fact: pd.DataFrame, category_col: str, supplier_col: str, value_col: str
) -> pd.DataFrame:
    """Spend e participacao percentual de cada fornecedor, dentro de cada
    categoria -- base compartilhada por compute_hhi_by_category e
    build_supplier_abc_curve, para nao duplicar a logica de agregacao."""
    df = _exclude_flagged_rows(df_fact.copy())
    df[category_col] = df[category_col].fillna(CATEGORIA_NAO_CLASSIFICADA)

    spend_por_fornecedor = (
        df.groupby([category_col, supplier_col])[value_col].sum().reset_index()
    )
    spend_por_categoria = spend_por_fornecedor.groupby(category_col)[value_col].transform("sum")
    spend_por_fornecedor["share_pct"] = 100 * spend_por_fornecedor[value_col] / spend_por_categoria
    return spend_por_fornecedor


def compute_hhi_by_category(
    df_fact: pd.DataFrame,
    category_col: str = "categoria_relevante",
    supplier_col: str = "supplier_key",
    value_col: str = "total_price",
) -> pd.DataFrame:
    """HHI, participacao do maior fornecedor (top1) e dos 3 maiores (top3)
    por categoria. Numero de grupos e pequeno (uma categoria por vez), a
    agregacao por groupby().apply() aqui e barata -- diferente do problema
    de performance que tivemos em build_dim_item (centenas de milhares de
    grupos)."""
    shares = _supplier_spend_shares(df_fact, category_col, supplier_col, value_col)

    def top_n_share(serie: pd.Series, n: int) -> float:
        return serie.sort_values(ascending=False).head(n).sum()

    resultado = shares.groupby(category_col).agg(
        n_fornecedores_distintos=(supplier_col, "nunique"),
    )
    resultado["hhi"] = shares.groupby(category_col)["share_pct"].apply(lambda s: (s**2).sum())
    resultado["top1_supplier_share_pct"] = shares.groupby(category_col)["share_pct"].apply(
        lambda s: top_n_share(s, 1)
    )
    resultado["top3_supplier_share_pct"] = shares.groupby(category_col)["share_pct"].apply(
        lambda s: top_n_share(s, 3)
    )
    resultado["classificacao_hhi"] = resultado["hhi"].apply(classify_hhi)

    return resultado.reset_index().sort_values("hhi", ascending=False).reset_index(drop=True)


def build_supplier_abc_curve(
    df_fact: pd.DataFrame,
    category: str | None = None,
    category_col: str = "categoria_relevante",
    supplier_col: str = "supplier_key",
    value_col: str = "total_price",
) -> pd.DataFrame:
    """Curva ABC (Pareto) de fornecedores por spend, dentro de uma
    categoria (ou universo inteiro, se category=None). Classe A = ate 80%
    do spend acumulado, B = ate 95%, C = resto."""
    df = _exclude_flagged_rows(df_fact.copy())
    if category is not None:
        df[category_col] = df[category_col].fillna(CATEGORIA_NAO_CLASSIFICADA)
        df = df[df[category_col] == category]

    if df.empty:
        return pd.DataFrame(columns=[supplier_col, value_col, "share_pct", "cum_share_pct", "classe_abc"])

    spend = df.groupby(supplier_col)[value_col].sum().sort_values(ascending=False).reset_index()
    total = spend[value_col].sum()
    spend["share_pct"] = 100 * spend[value_col] / total
    spend["cum_share_pct"] = spend["share_pct"].cumsum()
    spend["classe_abc"] = np.select(
        [spend["cum_share_pct"] <= 80, spend["cum_share_pct"] <= 95],
        ["A", "B"],
        default="C",
    )
    return spend
