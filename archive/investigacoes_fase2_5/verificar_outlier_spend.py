import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import date
from src.ingestion.pncp_bulk import local_path_for
from src.quality.checks import load_bronze_csv
from src.transformation.silver import apply_typing, remove_exact_duplicates, resolve_temporal_revisions
import pandas as pd

pd.set_option("display.max_colwidth", 80)
pd.set_option("display.width", 200)

df = load_bronze_csv(local_path_for(date(2026, 5, 22)))
df = apply_typing(df)
df, _ = remove_exact_duplicates(df)
df, _ = resolve_temporal_revisions(df)

top10 = df.nlargest(10, "valor_total_resultado")[
    ["descricao_resumida", "valor_total_resultado", "quantidade_resultado", "valor_unitario_resultado", "nome_fornecedor"]
]
print(top10.to_string(index=False))
print()
print("Soma dos top 10:", top10["valor_total_resultado"].sum())
print("Soma total do dia:", df["valor_total_resultado"].sum())
