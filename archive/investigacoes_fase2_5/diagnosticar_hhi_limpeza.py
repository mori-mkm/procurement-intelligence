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

pd.set_option("display.max_colwidth", 100)
pd.set_option("display.width", 220)

gold = load_gold_layer()
fact = gold["fact_purchase"]
dim_supplier = gold["dim_supplier"]
dim_item = gold["dim_item"]

limpeza = fact[fact["categoria_relevante"] == "Limpeza / Facilities"]
spend_por_fornecedor = limpeza.groupby("supplier_key")["total_price"].sum().sort_values(ascending=False)

top_fornecedor = spend_por_fornecedor.index[0]
print(f"Fornecedor dominante: {top_fornecedor}")
print(f"Spend desse fornecedor na categoria: {spend_por_fornecedor.iloc[0]:,.2f}")
print(f"Spend total da categoria: {spend_por_fornecedor.sum():,.2f}")
print()

info_fornecedor = dim_supplier[dim_supplier["supplier_key"] == top_fornecedor]
print("Info do fornecedor (dim_supplier):")
print(info_fornecedor.to_string(index=False))
print()

linhas_fornecedor = limpeza[limpeza["supplier_key"] == top_fornecedor]
print(f"Numero de transacoes desse fornecedor na categoria: {len(linhas_fornecedor)}")
print()

print("Top 10 transacoes por valor, desse fornecedor:")
top_transacoes = linhas_fornecedor.nlargest(10, "total_price")[["item_key", "total_price", "unit_price", "quantity", "date_key", "buyer_key"]]
print(top_transacoes.to_string(index=False))
print()

print("Itens (item_key) distintos comprados desse fornecedor nesta categoria:")
print(linhas_fornecedor["item_key"].value_counts().head(10))
