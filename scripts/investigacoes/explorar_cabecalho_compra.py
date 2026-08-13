import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import date
from src.ingestion.pncp_bulk import local_path_for, DATASET_COMPRA
from src.quality.checks import load_bronze_csv
import pandas as pd

pd.set_option("display.max_colwidth", 60)
pd.set_option("display.width", 200)

for dia in [date(2025, 12, 1), date(2026, 5, 22)]:
    print(f"=== {dia.isoformat()} ===")
    caminho = local_path_for(dia, DATASET_COMPRA)
    df = load_bronze_csv(caminho)

    print(f"Linhas: {len(df)} | Colunas: {len(df.columns)}")
    print()

    print("id_compra -- amostra e checagem de duplicidade:")
    print(df["id_compra"].head(5).tolist())
    print(f"id_compra duplicado: {df['id_compra'].duplicated().sum()} de {len(df)}")
    print()

    print("orgao_subrogado_cnpj -- taxa de preenchimento:")
    pct_preenchido = df["orgao_subrogado_cnpj"].notna().mean() * 100
    print(f"{pct_preenchido:.2f}% das compras tem orgao_subrogado_cnpj preenchido")
    if pct_preenchido > 0:
        print("Amostra de linhas com sub-rogacao:")
        cols = ["id_compra", "orgao_entidade_cnpj", "orgao_entidade_razao_social", "orgao_subrogado_cnpj", "orgao_subrogado_razao_social"]
        print(df[df["orgao_subrogado_cnpj"].notna()][cols].head(5).to_string(index=False))
    print()

    print("unidade_orgao_uf_sigla -- valores distintos e nulos:")
    print(f"nulos: {df['unidade_orgao_uf_sigla'].isna().mean()*100:.2f}%")
    print(df["unidade_orgao_uf_sigla"].value_counts(dropna=False).head(10))
    print()

    print("modalidade_nome -- valores distintos:")
    print(df["modalidade_nome"].value_counts(dropna=False))
    print()
