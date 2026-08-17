import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

import json
from src.transformation.gold import load_gold_layer
from src.analytics.price_baseline import build_price_baseline_report

gold = load_gold_layer()
fact = gold["fact_purchase"]

relatorio = build_price_baseline_report(fact)
print(json.dumps(relatorio, ensure_ascii=False, indent=2))
