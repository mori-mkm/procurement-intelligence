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
from src.ingestion.pncp_bulk_annual import local_parquet_path, DATASET_ITEM
from src.quality.checks import select_necessary_columns
from src.transformation.silver import build_silver_transformation_report

pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 200)

print("Recarregando os 3 anos brutos (para comparar colunas completas depois)...")
frames_brutos = {}
for ano in [2024, 2025, 2026]:
    caminho = local_parquet_path(ano, DATASET_ITEM)
    frames_brutos[ano] = pd.read_parquet(caminho)
    print(f"  {ano}: {len(frames_brutos[ano])} linhas brutas")
print()

print("Reprocessando Silver combinado (mesmo pipeline de antes)...")
frames_cortados = [select_necessary_columns(df) for df in frames_brutos.values()]
df_combinado = pd.concat(frames_cortados, ignore_index=True)
relatorio_silver, df_silver = build_silver_transformation_report(df_combinado)
print(f"  Silver: {len(df_silver)} linhas")
print()

chave = ["id_compra_item", "cod_fornecedor"]
dup_mask = df_silver.duplicated(subset=chave, keep=False)
grupos_dup = df_silver[dup_mask].groupby(chave)
grupos_violacao_ids = grupos_dup.filter(lambda g: not g["resultado_conflitante"].any())[chave].drop_duplicates()
print(f"Total de grupos violando o grao (nao flagados): {len(grupos_violacao_ids)}")
print()

alvo = grupos_violacao_ids.iloc[0]
id_item_alvo, fornecedor_alvo = alvo["id_compra_item"], alvo["cod_fornecedor"]
print(f"Investigando grupo de exemplo: id_compra_item={id_item_alvo}, cod_fornecedor={fornecedor_alvo}")
print()

for ano, df_bruto in frames_brutos.items():
    achado = df_bruto[
        (df_bruto["id_compra_item"] == id_item_alvo) & (df_bruto["cod_fornecedor"] == fornecedor_alvo)
    ]
    if not achado.empty:
        print(f"=== Encontrado no arquivo BRUTO de {ano} ({len(achado)} linha(s)) ===")
        print(achado.T.to_string())
        print()
