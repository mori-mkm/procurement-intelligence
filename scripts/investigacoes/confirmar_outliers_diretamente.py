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

pd.set_option("display.max_colwidth", 60)
pd.set_option("display.width", 200)

gold = load_gold_layer()
fact = gold["fact_purchase"]

print(f"Total de linhas: {len(fact)}")
print(f"Outliers flagados (is_value_outlier=True): {fact['is_value_outlier'].sum()} ({100*fact['is_value_outlier'].mean():.4f}%)")
print()
print("Distribuicao de outlier_reason (entre os flagados):")
print(fact.loc[fact["is_value_outlier"], "outlier_reason"].value_counts())
print()

print(f"Linhas em grupos pequenos demais para avaliar (n_transacoes_grupo_outlier_check < 5): {(fact['n_transacoes_grupo_outlier_check'] < 5).sum()}")
print()

print("=== Top 20 maiores transacoes ENTRE AS NAO-FLAGADAS (deveria estar limpo agora) ===")
nao_flagadas = fact[~fact["is_value_outlier"]]
top20_limpo = nao_flagadas.nlargest(20, "total_price")[
    ["item_key", "unit_price", "quantity", "total_price", "n_transacoes_grupo_outlier_check", "categoria_relevante"]
]
print(top20_limpo.to_string(index=False))
print()

spend_sem_outlier = nao_flagadas["total_price"].sum()
spend_total = fact["total_price"].sum()
print(f"Spend total (com outlier): {spend_total:,.2f}")
print(f"Spend total (sem outlier): {spend_sem_outlier:,.2f}")
print(f"Reducao: {100*(spend_total-spend_sem_outlier)/spend_total:.2f}%")
