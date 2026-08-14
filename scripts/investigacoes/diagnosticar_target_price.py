"""
Fase 13.6 - Diagnostico de qualidade do target de preco.

Objetivo:
- medir precos nulos, zero e negativos;
- medir quantidades nulas, zero e negativas;
- verificar distribuicao temporal;
- entender se unit_price <= 0 deve ser excluido da modelagem.

Nenhuma transformacao ou dado e alterado por este script.
"""

import sys
from pathlib import Path

import pandas as pd


def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()

    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai

    raise RuntimeError("Nao encontrei a raiz do projeto")


RAIZ = achar_raiz_projeto(Path(__file__))
sys.path.insert(0, str(RAIZ))


from src.transformation.gold import load_gold_layer
from src.analytics.price_baseline import prepare_baseline_dataset


def main():
    print("=" * 80)
    print("FASE 13.6 - DIAGNOSTICO DO TARGET DE PRECO")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. Carregar exatamente o universo usado na modelagem
    # ---------------------------------------------------------
    print("\n[1/5] Carregando Gold...")

    gold = load_gold_layer()
    fact = gold["fact_purchase"]

    print(f"Fact purchase: {len(fact):,}")

    print("\n[2/5] Aplicando escopo atual de Price Intelligence...")

    df = prepare_baseline_dataset(fact)

    print(f"Dataset de modelagem: {len(df):,}")

    # Conversao defensiva apenas para diagnostico
    price = pd.to_numeric(
        df["unit_price"],
        errors="coerce",
    )

    quantity = pd.to_numeric(
        df["quantity"],
        errors="coerce",
    )

    # ---------------------------------------------------------
    # 2. Qualidade geral
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("QUALIDADE GERAL")
    print("=" * 80)

    diagnostics = {
        "unit_price_null": price.isna().sum(),
        "unit_price_zero": price.eq(0).sum(),
        "unit_price_negative": price.lt(0).sum(),
        "unit_price_non_positive": price.le(0).sum(),
        "quantity_null": quantity.isna().sum(),
        "quantity_zero": quantity.eq(0).sum(),
        "quantity_negative": quantity.lt(0).sum(),
        "quantity_non_positive": quantity.le(0).sum(),
    }

    for name, value in diagnostics.items():
        pct = 100 * value / len(df)

        print(
            f"{name:<28}: "
            f"{value:>8,} "
            f"({pct:>8.4f}%)"
        )

    # ---------------------------------------------------------
    # 3. Por ano
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("PROBLEMAS POR ANO")
    print("=" * 80)

    audit = pd.DataFrame(
        {
            "ano": df["ano"],
            "price_null": price.isna(),
            "price_zero": price.eq(0),
            "price_negative": price.lt(0),
            "price_non_positive": price.le(0),
            "quantity_null": quantity.isna(),
            "quantity_zero": quantity.eq(0),
            "quantity_negative": quantity.lt(0),
        },
        index=df.index,
    )

    por_ano = audit.groupby("ano").agg(
        n=("ano", "size"),
        price_null=("price_null", "sum"),
        price_zero=("price_zero", "sum"),
        price_negative=("price_negative", "sum"),
        price_non_positive=("price_non_positive", "sum"),
        quantity_null=("quantity_null", "sum"),
        quantity_zero=("quantity_zero", "sum"),
        quantity_negative=("quantity_negative", "sum"),
    )

    por_ano["pct_price_non_positive"] = (
        100
        * por_ano["price_non_positive"]
        / por_ano["n"]
    )

    print(por_ano.to_string())

    # ---------------------------------------------------------
    # 4. Onde estao os precos nao positivos?
    # ---------------------------------------------------------
    problematicos = df[
        price.isna()
        | price.le(0)
    ].copy()

    print("\n" + "=" * 80)
    print("PRECO NULO OU <= 0 POR CATEGORIA")
    print("=" * 80)

    if problematicos.empty:
        print("Nenhum registro encontrado.")
    else:
        por_categoria = (
            problematicos
            .groupby(
                "categoria_relevante",
                dropna=False,
            )
            .size()
            .sort_values(ascending=False)
        )

        print(
            por_categoria
            .head(20)
            .to_string()
        )

    # ---------------------------------------------------------
    # 5. Amostra para inspecao
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("AMOSTRA DE REGISTROS COM PRECO NULO OU <= 0")
    print("=" * 80)

    colunas_desejadas = [
        "date_key",
        "ano",
        "item_key",
        "categoria_relevante",
        "quantity",
        "unit_price",
        "total_price",
        "unit_flag",
        "supplier_key",
        "buyer_key",
    ]

    colunas = [
        col
        for col in colunas_desejadas
        if col in problematicos.columns
    ]

    if problematicos.empty:
        print("Nenhum registro problematico.")
    else:
        print(
            problematicos[colunas]
            .head(30)
            .to_string(index=False)
        )

    print("\n" + "=" * 80)
    print("DIAGNOSTICO CONCLUIDO")
    print("=" * 80)


if __name__ == "__main__":
    main()