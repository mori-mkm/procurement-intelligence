import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import date
from src.ingestion.pncp_bulk import local_path_for, DATASET_COMPRA
import pandas as pd

caminho = local_path_for(date(2025, 12, 1), DATASET_COMPRA)
df_bruto = pd.read_csv(caminho, sep=",", encoding="utf-8", low_memory=False)

print("dtype de orgao_entidade_cnpj (sem forcar tipo):", df_bruto["orgao_entidade_cnpj"].dtype)
print("Amostra:", df_bruto["orgao_entidade_cnpj"].head(5).tolist())
print()
print("dtype de id_compra (sem forcar tipo):", df_bruto["id_compra"].dtype)
print("Amostra:", df_bruto["id_compra"].head(5).tolist())
