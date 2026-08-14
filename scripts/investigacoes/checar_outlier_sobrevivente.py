import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

from src.transformation.gold import load_gold_layer
from src.analytics.price_baseline import prepare_baseline_dataset

gold = load_gold_layer()
fact = gold["fact_purchase"]

df_prep = prepare_baseline_dataset(fact)

print("unit_price >= 1.000.000 sobrevivendo apos prepare_baseline_dataset:")
extremos = df_prep[df_prep["unit_price"] >= 1_000_000]
print(f"N linhas: {len(extremos)}")
print(extremos[["item_key", "unit_price", "is_value_outlier"]].head(10).to_string(index=False))
