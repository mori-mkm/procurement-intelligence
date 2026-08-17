import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import date
from src.ingestion.pncp_bulk import local_path_for
from src.quality.checks import load_bronze_csv
from src.transformation.silver import apply_typing, remove_exact_duplicates, resolve_temporal_revisions
import pandas as pd

pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", None)

df = load_bronze_csv(local_path_for(date(2026, 5, 22)))
df = apply_typing(df)
df, _ = remove_exact_duplicates(df)
df, _ = resolve_temporal_revisions(df)

compra_alvo = "15478305900012026"
grupo = df[df["id_compra"] == compra_alvo].sort_values(["id_compra_item", "cod_fornecedor"])

print(f"Total de linhas para id_compra={compra_alvo}: {len(grupo)}")
print()

colunas_interesse = [
    "id_compra_item", "cod_fornecedor", "COD_RESULTADO_ITEM",
    "valor_unitario_resultado", "quantidade_resultado", "valor_total_resultado",
    "data_resultado", "data_atualizacao_pncp", "data_inclusao_pncp",
    "situacao_compra_item", "situacao_compra_item_nome",
    "numero_controle_PNCP_compra", "ID_contratacao_PNCP",
    "descricao_resumida", "unidade_medida",
]
colunas_interesse = [c for c in colunas_interesse if c in grupo.columns]

for id_item, subgrupo in grupo.groupby("id_compra_item"):
    if len(subgrupo) > 1:
        print(f"=== id_compra_item = {id_item} ({len(subgrupo)} linhas) ===")
        print(subgrupo[colunas_interesse].T.to_string())
        print()
