import sys
from pathlib import Path
from collections import Counter
import re

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

gold = load_gold_layer()
fact = gold["fact_purchase"]

relevante = fact[fact["categoria_relevante"].notna()].copy()
extremo = flag_extreme_by_global_median(fact)
relevante_limpo = relevante[~relevante["is_value_outlier"].fillna(False) & ~extremo.reindex(relevante.index)]

n_por_item = relevante_limpo.groupby("item_key").size()
itens_cauda = n_por_item[n_por_item < 5].index

STOPWORDS = {
    "de", "da", "do", "das", "dos", "e", "com", "para", "em", "a", "o", "as", "os",
    "ate", "sem", "por", "no", "na", "ou", "um", "uma", "tipo", "sistema",
}

contador_palavras = Counter()
contador_spend_por_palavra = {}

spend_por_item = relevante_limpo[relevante_limpo["item_key"].isin(itens_cauda)].groupby("item_key")["total_price"].sum()

for item_key in itens_cauda:
    palavras = re.findall(r"[a-z]+", item_key)
    palavras_unicas = set(p for p in palavras if len(p) > 3 and p not in STOPWORDS)
    for p in palavras_unicas:
        contador_palavras[p] += 1
        contador_spend_por_palavra[p] = contador_spend_por_palavra.get(p, 0) + spend_por_item.get(item_key, 0)

print(f"Total de item_key na cauda longa (<5 transacoes): {len(itens_cauda)}")
print(f"Spend total dessa cauda: {spend_por_item.sum():,.2f}")
print()
print("Top 40 palavras mais frequentes na cauda (n_itens_distintos_contendo_palavra | spend_total_associado):")
for palavra, n in contador_palavras.most_common(40):
    spend = contador_spend_por_palavra[palavra]
    print(f"  {palavra:30s} {n:5d} itens | R$ {spend:>18,.2f}")
