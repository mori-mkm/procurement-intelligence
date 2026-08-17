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

gold = load_gold_layer()
fact = gold["fact_purchase"]

print("=== Diagnostico 2: join sem match, por data ===")
sem_match = fact[fact["unidade_orgao_uf_sigla"].isna()]
com_match = fact[fact["unidade_orgao_uf_sigla"].notna()]

print(f"Linhas sem match: {len(sem_match)} ({100*len(sem_match)/len(fact):.2f}%)")
print()
print("date_key -- SEM match (deveria concentrar em datas fora de 2024-2026):")
print(sem_match["date_key"].describe())
print()
print("date_key -- COM match:")
print(com_match["date_key"].describe())
print()

pct_pre_2024 = (sem_match["date_key"] < 20240101).mean() * 100
print(f"% das linhas sem match com date_key < 2024-01-01: {pct_pre_2024:.2f}%")
