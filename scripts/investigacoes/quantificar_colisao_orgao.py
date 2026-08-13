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

CACHE_PATH = Path("data/_scratch_silver_2024_2026.parquet")
df_silver = pd.read_parquet(CACHE_PATH)

chave = ["id_compra_item", "cod_fornecedor"]
dup_mask = df_silver.duplicated(subset=chave, keep=False)
grupos_dup = df_silver[dup_mask].groupby(chave)

n_orgao_distinto = grupos_dup["orgao_entidade_cnpj"].nunique()
grupos_com_orgao_diferente = (n_orgao_distinto > 1).sum()
total_grupos_dup = len(n_orgao_distinto)

print(f"Total de grupos duplicados (id_compra_item x cod_fornecedor): {total_grupos_dup}")
print(f"Grupos com orgao_entidade_cnpj DIFERENTE entre as linhas (colisao real de ID entre orgaos): {grupos_com_orgao_diferente} ({100*grupos_com_orgao_diferente/total_grupos_dup:.1f}%)")
