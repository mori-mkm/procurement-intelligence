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
from src.transformation.gold import (
    load_dim_buyer_from_annual, build_dim_item, build_fact_purchase, validate_fact_purchase_grain,
)
import json

dias = [date(2025, 12, 1), date(2026, 5, 22)]
frames = []
for dia in dias:
    df_bronze = load_bronze_csv(local_path_for(dia))
    _, df_silver = build_silver_transformation_report(df_bronze)
    frames.append(df_silver)

df_item_combinado = pd.concat(frames, ignore_index=True)

dim_buyer = load_dim_buyer_from_annual([2024, 2025, 2026])
dim_item = build_dim_item(df_item_combinado)

fact, stats_build = build_fact_purchase(df_item_combinado, dim_buyer, dim_item)
print("Estatisticas de construcao:", json.dumps(stats_build, ensure_ascii=False, indent=2))
print()

validacao = validate_fact_purchase_grain(fact)
print("Validacao de grao:", json.dumps(validacao, ensure_ascii=False, indent=2))
print()

print("Amostra de 5 linhas do fact_purchase final:")
cols = ["purchase_item_id", "supplier_key", "item_key", "buyer_key", "unidade_orgao_uf_sigla", "date_key", "quantity", "unit_price", "unit_flag", "categoria_relevante"]
print(fact[cols].head(5).to_string(index=False))
print()

print("Spend total (bruto, sem filtrar resultado_conflitante):", fact["total_price"].sum())
