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
from src.ingestion.pncp_bulk_annual import local_parquet_path, DATASET_COMPRA

anos = [2024, 2025, 2026]
frames = {}
for ano in anos:
    df = pd.read_parquet(local_parquet_path(ano, DATASET_COMPRA))
    frames[ano] = df
    n_dup_interno = df["id_compra"].duplicated().sum()
    print(f"Ano {ano}: {len(df)} linhas, {n_dup_interno} id_compra duplicado DENTRO do proprio arquivo")

print()

ids_por_ano = {ano: set(df["id_compra"]) for ano, df in frames.items()}
print("Sobreposicao de id_compra ENTRE anos:")
print(f"  2024 ∩ 2025: {len(ids_por_ano[2024] & ids_por_ano[2025])}")
print(f"  2025 ∩ 2026: {len(ids_por_ano[2025] & ids_por_ano[2026])}")
print(f"  2024 ∩ 2026: {len(ids_por_ano[2024] & ids_por_ano[2026])}")
print()

df_completo = pd.concat(frames.values(), ignore_index=True)
duplicados = df_completo[df_completo["id_compra"].duplicated(keep=False)].sort_values("id_compra")
print(f"Total de linhas envolvidas em duplicatas (combinado): {len(duplicados)}")
print()
print("Amostra de um caso duplicado, todas as colunas relevantes:")
primeiro_id_dup = duplicados["id_compra"].iloc[0]
cols_interesse = ["id_compra", "data_publicacao_pncp", "data_atualizacao_pncp", "orgao_entidade_razao_social", "modalidade_nome", "situacao_compra_nome_pncp"]
cols_interesse = [c for c in cols_interesse if c in duplicados.columns]
print(duplicados[duplicados["id_compra"] == primeiro_id_dup][cols_interesse].to_string(index=False))
