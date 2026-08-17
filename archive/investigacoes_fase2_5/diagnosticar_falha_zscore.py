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
import numpy as np
from src.transformation.gold import load_gold_layer

pd.set_option("display.max_colwidth", 60)
pd.set_option("display.width", 200)

gold = load_gold_layer()
fact = gold["fact_purchase"]

print("=== Caso 1: 'prestacao de servicos bancarios' (465 transacoes, nao flagado, valor bilhoes) ===")
grupo = fact[fact["item_key"] == "prestacao de servicos bancarios"]
print(f"N transacoes no grupo: {len(grupo)}")
print(grupo["unit_price"].describe())
print()
print("z_log_unit_price - estatisticas do grupo inteiro:")
print(grupo["z_log_unit_price"].describe())
print()
print("Top 10 maiores unit_price do grupo, com o z calculado:")
print(grupo.nlargest(10, "unit_price")[["unit_price", "z_log_unit_price", "is_value_outlier"]].to_string(index=False))
print()

print("=== Caso 2: 'consulta medica - nefrologia' (34 transacoes) ===")
grupo2 = fact[fact["item_key"] == "consulta medica - nefrologia"]
print(grupo2[["unit_price", "quantity", "total_price", "z_log_unit_price", "z_log_quantity", "is_value_outlier"]].sort_values("total_price", ascending=False).to_string(index=False))
