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
import pandas as pd
from src.ingestion.pncp_bulk import local_path_for
from src.quality.checks import load_bronze_csv
from src.transformation.silver import build_silver_transformation_report
from src.transformation.gold import build_dim_item, build_dim_supplier, build_dim_date

dias = [date(2025, 12, 1), date(2026, 5, 22)]
frames = []
for dia in dias:
    df_bronze = load_bronze_csv(local_path_for(dia))
    _, df_silver = build_silver_transformation_report(df_bronze)
    frames.append(df_silver)

df_fact = pd.concat(frames, ignore_index=True)
print(f"Total combinado (2 dias): {len(df_fact)} linhas")
print()

dim_supplier = build_dim_supplier(df_fact)
print(f"dim_supplier: {len(dim_supplier)} fornecedores distintos")
print("Top 10 por volume:")
print(dim_supplier.head(10)[["supplier_key", "nome_fornecedor", "n_transacoes", "n_produtos_servicos_distintos"]].to_string(index=False))
print()

dim_date = build_dim_date(date(2024, 1, 1), date(2026, 12, 31))
print(f"dim_date: {len(dim_date)} linhas")
print(dim_date.head(3).to_string(index=False))
