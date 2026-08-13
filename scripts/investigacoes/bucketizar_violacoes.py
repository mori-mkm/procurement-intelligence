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
grupos_dup_df = df_silver[dup_mask]

# mesmo filtro do pipeline: so grupos NAO flagados como conflitante
grupos_nao_flagados_df = grupos_dup_df.groupby(chave).filter(lambda g: not g["resultado_conflitante"].any())
g = grupos_nao_flagados_df.groupby(chave)

n_orgao = g["orgao_entidade_cnpj"].nunique()
n_valor_unit_res = g["valor_unitario_resultado"].nunique(dropna=False)
n_valor_tot_res = g["valor_total_resultado"].nunique(dropna=False)
n_qtd_res = g["quantidade_resultado"].nunique(dropna=False)
n_data_res = g["data_resultado"].nunique(dropna=False)

mesmo_orgao = n_orgao == 1
mesmo_resultado = (n_valor_unit_res == 1) & (n_valor_tot_res == 1) & (n_qtd_res == 1) & (n_data_res == 1)

bucket = pd.Series("outro_nao_explicado", index=n_orgao.index)
bucket[~mesmo_orgao] = "orgao_diferente_colisao_real"
bucket[mesmo_orgao & mesmo_resultado] = "mesmo_resultado_so_metadado_estimado_difere"

print("Total de grupos nao flagados:", len(bucket))
print()
print(bucket.value_counts())
print()
print("Percentuais:")
print((100 * bucket.value_counts() / len(bucket)).round(2))
