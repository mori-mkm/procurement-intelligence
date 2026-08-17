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
from src.analytics.spend_analytics import (
    compute_spend_by_category, compute_hhi_by_category, build_supplier_abc_curve,
)

pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 40)

print("Carregando Gold persistido...")
gold = load_gold_layer()
fact = gold["fact_purchase"]
dim_supplier = gold["dim_supplier"]
print(f"  {len(fact)} transacoes")
print()

print("=== Spend por categoria relevante ===")
spend_cat = compute_spend_by_category(fact)
print(spend_cat.to_string(index=False))
print()

print("=== HHI e concentracao por categoria ===")
hhi_cat = compute_hhi_by_category(fact)
print(hhi_cat.to_string(index=False))
print()

print("=== Curva ABC dentro de TI / Informatica (maior categoria curada) ===")
abc_ti = build_supplier_abc_curve(fact, category="TI / Informatica")
abc_ti = abc_ti.merge(dim_supplier[["supplier_key", "nome_fornecedor"]], on="supplier_key", how="left")
distribuicao_classes = abc_ti["classe_abc"].value_counts().to_dict()
print(f"Total de fornecedores na categoria: {len(abc_ti)}")
print(f"Distribuicao de classes: {distribuicao_classes}")
print()
print("Top 15 fornecedores (Classe A):")
print(abc_ti.head(15)[["supplier_key", "nome_fornecedor", "total_price", "share_pct", "cum_share_pct", "classe_abc"]].to_string(index=False))
