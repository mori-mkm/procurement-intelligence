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

pd.set_option("display.max_colwidth", 80)
pd.set_option("display.width", 200)

gold = load_gold_layer()
fact = gold["fact_purchase"]

print("Estatisticas de total_price no fact_purchase inteiro:")
print(fact["total_price"].describe())
print()

print("Top 20 maiores transacoes (total_price) do dataset inteiro:")
top20 = fact.nlargest(20, "total_price")[["item_key", "supplier_key", "unit_price", "quantity", "total_price", "date_key", "categoria_relevante"]]
print(top20.to_string(index=False))
print()

# Quanto do spend total esta concentrado nas 20 maiores transacoes?
spend_top20 = top20["total_price"].sum()
spend_total_geral = fact["total_price"].sum()
print(f"Spend das 20 maiores transacoes: {spend_top20:,.2f}")
print(f"Spend total geral: {spend_total_geral:,.2f}")
print(f"Percentual: {100*spend_top20/spend_total_geral:.2f}%")
