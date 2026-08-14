import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

import pandas as pd
from src.transformation.gold import load_gold_layer
from src.analytics.spend_analytics import flag_extreme_by_global_median

pd.set_option("display.width", 200)

gold = load_gold_layer()
fact = gold["fact_purchase"]

relevante = fact[fact["categoria_relevante"].notna()].copy()
print(f"Total no universo relevante (8 categorias curadas): {len(relevante)} transacoes")
print()

# aplica as duas camadas de limpeza de outlier antes de medir volume
extremo = flag_extreme_by_global_median(fact)
relevante_limpo = relevante[~relevante["is_value_outlier"].fillna(False) & ~extremo.reindex(relevante.index)]
print(f"Apos exclusao de outliers: {len(relevante_limpo)} transacoes")
print()

n_por_item = relevante_limpo.groupby("item_key").size().sort_values(ascending=False)
print(f"Total de item_key distintos no universo relevante: {len(n_por_item)}")
print()

print("Distribuicao de n_transacoes por item_key (percentis):")
print(n_por_item.describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]))
print()

# quantos itens (e que fracao do SPEND) sobrariam em cada threshold candidato
spend_por_item = relevante_limpo.groupby("item_key")["total_price"].sum()
spend_total_relevante = spend_por_item.sum()

print("Cobertura por threshold de volume minimo (n transacoes por item_key):")
for limiar in [1, 2, 3, 5, 10, 20, 30]:
    itens_ok = n_por_item[n_por_item >= limiar].index
    n_itens = len(itens_ok)
    spend_coberto = spend_por_item.reindex(itens_ok).sum()
    pct_itens = 100 * n_itens / len(n_por_item)
    pct_spend = 100 * spend_coberto / spend_total_relevante
    print(f"  min >= {limiar:3d} transacoes: {n_itens:6d} itens ({pct_itens:5.1f}% dos itens) cobrem {pct_spend:5.1f}% do spend relevante")

print()
print("Top 15 item_key com MAIS transacoes (candidatos a baseline mais confiavel):")
print(n_por_item.head(15))
