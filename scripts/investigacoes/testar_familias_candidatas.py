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

pd.set_option("display.max_colwidth", 70)
pd.set_option("display.width", 200)

gold = load_gold_layer()
fact = gold["fact_purchase"]
relevante = fact[fact["categoria_relevante"].notna()].copy()
extremo = flag_extreme_by_global_median(fact)
limpo = relevante[~relevante["is_value_outlier"].fillna(False) & ~extremo.reindex(relevante.index)]

n_por_item = limpo.groupby("item_key").size()
cauda = limpo[limpo["item_key"].isin(n_por_item[n_por_item < 5].index)]

print("=== Candidata: suprimento_impressora (cartucho+impressora OU toner OU tinta+impressora) ===")
mask1 = (
    (cauda["item_key"].str.contains("cartucho") & cauda["item_key"].str.contains("impressora"))
    | cauda["item_key"].str.contains("toner")
    | (cauda["item_key"].str.contains("tinta") & cauda["item_key"].str.contains("impressora"))
)
grupo1 = cauda[mask1]
print(f"N itens distintos: {grupo1['item_key'].nunique()} | N transacoes: {len(grupo1)}")
print("Amostra de item_key distintos (ate 20) com unit_price:")
amostra1 = grupo1.groupby("item_key")["unit_price"].agg(["median", "count"]).sort_values("count", ascending=False).head(20)
print(amostra1.to_string())
print()

print("=== Candidata: licenciamento_software (cessao+programas+computador) ===")
mask2 = (
    cauda["item_key"].str.contains("cessao")
    & cauda["item_key"].str.contains("programas")
    & cauda["item_key"].str.contains("computador")
)
grupo2 = cauda[mask2]
print(f"N itens distintos: {grupo2['item_key'].nunique()} | N transacoes: {len(grupo2)}")
amostra2 = grupo2.groupby("item_key")["unit_price"].agg(["median", "count"]).sort_values("count", ascending=False).head(20)
print(amostra2.to_string())
