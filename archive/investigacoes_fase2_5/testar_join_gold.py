import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto (pasta .git) subindo a partir de " + str(caminho_inicial))

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

from datetime import date
from src.ingestion.pncp_bulk import local_path_for, DATASET_COMPRA
from src.quality.checks import load_bronze_csv
from src.transformation.silver import build_silver_transformation_report
from src.transformation.gold import build_dim_buyer, validate_dim_buyer_grain, join_fact_with_buyer
import json

for dia in [date(2025, 12, 1), date(2026, 5, 22)]:
    print(f"=== {dia.isoformat()} ===")

    df_item_bronze = load_bronze_csv(local_path_for(dia))
    _, df_item_silver = build_silver_transformation_report(df_item_bronze)

    df_cabecalho = load_bronze_csv(local_path_for(dia, DATASET_COMPRA))
    dim_buyer = build_dim_buyer(df_cabecalho)

    print("Validação do grão de dim_buyer:", validate_dim_buyer_grain(dim_buyer))

    df_fact, stats_join = join_fact_with_buyer(df_item_silver, dim_buyer)
    print("Estatísticas do join:", json.dumps(stats_join, ensure_ascii=False, indent=2))

    print("\nDistribuição de UF no fact (top 10):")
    print(df_fact["unidade_orgao_uf_sigla"].value_counts(dropna=False).head(10))
    print()
