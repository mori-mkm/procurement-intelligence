import sys, time
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

import pandas as pd
from src.ingestion.pncp_bulk_annual import local_parquet_path, DATASET_ITEM
from src.quality.checks import select_necessary_columns, NECESSARY_COLUMNS
from src.transformation.silver import build_silver_transformation_report

pd.set_option("display.max_colwidth", 80)
pd.set_option("display.width", 220)

CACHE_PATH = Path("data/_scratch_silver_2024_2026.parquet")
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

if CACHE_PATH.exists():
    print(f"Reaproveitando cache de {CACHE_PATH} (apague o arquivo se quiser forcar recalculo)")
    df_silver = pd.read_parquet(CACHE_PATH)
else:
    print("Carregando e processando os 3 anos (sem cache ainda)...")
    t0 = time.time()
    frames = []
    for ano in [2024, 2025, 2026]:
        caminho = local_parquet_path(ano, DATASET_ITEM)
        df_ano = select_necessary_columns(pd.read_parquet(caminho))
        frames.append(df_ano)
    df_combinado = pd.concat(frames, ignore_index=True)
    _, df_silver = build_silver_transformation_report(df_combinado)
    df_silver.to_parquet(CACHE_PATH, index=False)
    print(f"  Silver: {len(df_silver)} linhas, {time.time()-t0:.1f}s -- cache salvo em {CACHE_PATH}")

print()

chave = ["id_compra_item", "cod_fornecedor"]
dup_mask = df_silver.duplicated(subset=chave, keep=False)
grupos_dup = df_silver[dup_mask].groupby(chave)
grupos_violacao = grupos_dup.filter(lambda g: not g["resultado_conflitante"].any())
grupos_violacao_ids = grupos_violacao[chave].drop_duplicates()
print(f"Total de grupos violando o grao (nao flagados): {len(grupos_violacao_ids)}")
print()

# Para uma amostra de grupos, identificar EXATAMENTE quais colunas diferem
colunas_para_comparar = [c for c in df_silver.columns if c not in chave]
contagem_colunas_diferentes = {c: 0 for c in colunas_para_comparar}
amostra_ids = grupos_violacao_ids.head(200)

for _, linha_id in amostra_ids.iterrows():
    grupo = df_silver[
        (df_silver["id_compra_item"] == linha_id["id_compra_item"]) &
        (df_silver["cod_fornecedor"] == linha_id["cod_fornecedor"])
    ]
    for col in colunas_para_comparar:
        if grupo[col].astype(str).nunique() > 1:
            contagem_colunas_diferentes[col] += 1

print("Em uma amostra de 200 grupos violando o grao, quantos tiveram cada coluna DIFERENTE entre as linhas duplicadas:")
resultado_ordenado = sorted(contagem_colunas_diferentes.items(), key=lambda x: -x[1])
for col, n in resultado_ordenado:
    if n > 0:
        print(f"  {col}: {n} de 200 grupos ({100*n/200:.1f}%)")

print()
print("=== Exemplo detalhado de 1 grupo (todas as colunas, lado a lado) ===")
primeiro_id = amostra_ids.iloc[0]
grupo_exemplo = df_silver[
    (df_silver["id_compra_item"] == primeiro_id["id_compra_item"]) &
    (df_silver["cod_fornecedor"] == primeiro_id["cod_fornecedor"])
]
print(grupo_exemplo.T.to_string())
