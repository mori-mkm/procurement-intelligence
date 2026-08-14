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

pd.set_option("display.max_colwidth", 50)
pd.set_option("display.width", 220)

gold = load_gold_layer()
fact = gold["fact_purchase"]

nao_flagadas = fact[~fact["is_value_outlier"]]
top10 = nao_flagadas.nlargest(10, "total_price")

cols = ["item_key", "unit_price", "quantity", "total_price",
        "z_log_unit_price", "z_log_quantity",
        "n_transacoes_grupo_outlier_check", "is_value_outlier"]
print(top10[cols].to_string(index=False))
