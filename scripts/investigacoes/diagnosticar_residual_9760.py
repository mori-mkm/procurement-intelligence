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
from src.quality.checks import select_necessary_columns
from src.transformation.silver import build_silver_transformation_report

CACHE_PATH = Path("data/_scratch_silver_2024_2026_v2.parquet")

if CACHE_PATH.exists():
    print("Reaproveitando cache v2...")
    df_silver = pd.read_parquet(CACHE_PATH)
else:
    print("Recalculando Silver (com a correcao mais recente)...")
    t0 = time.time()
    frames = []
    for ano in [2024, 2025, 2026]:
        caminho = local_parquet_path(ano, DATASET_ITEM)
        frames.append(select_necessary_columns(pd.read_parquet(caminho)))
    df_combinado = pd.concat(frames, ignore_index=True)
    _, df_silver = build_silver_transformation_report(df_combinado)
    df_silver.to_parquet(CACHE_PATH, index=False)
    print(f"  {len(df_silver)} linhas, {time.time()-t0:.1f}s")

print()

chave = ["id_compra_item", "cod_fornecedor"]
dup_mask = df_silver.duplicated(subset=chave, keep=False)
grupos_nao_flagados_df = df_silver[dup_mask].groupby(chave).filter(lambda g: not g["resultado_conflitante"].any())
print(f"Total de grupos nao flagados (deve bater com 9760 da rodada anterior): {grupos_nao_flagados_df.groupby(chave).ngroups}")
print()

colunas_para_comparar = [c for c in df_silver.columns if c not in chave]
contagem = {c: 0 for c in colunas_para_comparar}

amostra_chaves = grupos_nao_flagados_df[chave].drop_duplicates().head(300)
for _, linha_id in amostra_chaves.iterrows():
    grupo = df_silver[
        (df_silver["id_compra_item"] == linha_id["id_compra_item"]) &
        (df_silver["cod_fornecedor"] == linha_id["cod_fornecedor"])
    ]
    for col in colunas_para_comparar:
        if grupo[col].astype(str).nunique() > 1:
            contagem[col] += 1

print("Em amostra de 300 grupos, quantos tiveram cada coluna DIFERENTE:")
for col, n in sorted(contagem.items(), key=lambda x: -x[1]):
    if n > 0:
        print(f"  {col}: {n} de 300 ({100*n/300:.1f}%)")

print()
print("=== Exemplo de grupo onde SO unidade_medida ou descricao_resumida difere ===")
for _, linha_id in amostra_chaves.iterrows():
    grupo = df_silver[
        (df_silver["id_compra_item"] == linha_id["id_compra_item"]) &
        (df_silver["cod_fornecedor"] == linha_id["cod_fornecedor"])
    ]
    diffs = [c for c in colunas_para_comparar if grupo[c].astype(str).nunique() > 1]
    if set(diffs) <= {"unidade_medida", "descricao_resumida"} and len(diffs) > 0:
        print(f"Colunas diferentes: {diffs}")
        for col in diffs:
            print(f"  {col}: {grupo[col].tolist()}")
        break
