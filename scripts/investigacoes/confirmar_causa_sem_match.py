import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

from datetime import date
from src.ingestion.pncp_bulk import local_path_for, DATASET_COMPRA
from src.quality.checks import load_bronze_csv
from src.transformation.silver import build_silver_transformation_report
from src.transformation.gold import build_dim_buyer, join_fact_with_buyer
import pandas as pd

dia = date(2025, 12, 1)

df_item_bronze = load_bronze_csv(local_path_for(dia))
_, df_item_silver = build_silver_transformation_report(df_item_bronze)

df_cabecalho = load_bronze_csv(local_path_for(dia, DATASET_COMPRA))
dim_buyer = build_dim_buyer(df_cabecalho)

df_fact, _ = join_fact_with_buyer(df_item_silver, dim_buyer)

sem_match = df_fact[df_fact["unidade_orgao_uf_sigla"].isna()]
com_match = df_fact[df_fact["unidade_orgao_uf_sigla"].notna()]

print("data_inclusao_pncp -- linhas SEM match no buyer:")
print(sem_match["data_inclusao_pncp"].describe())
print()
print("data_inclusao_pncp -- linhas COM match no buyer:")
print(com_match["data_inclusao_pncp"].describe())
print()

print("id_compra distintos SEM match:", sem_match["id_compra"].nunique())
print("id_compra distintos COM match:", com_match["id_compra"].nunique())
