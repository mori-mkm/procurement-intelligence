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
from src.transformation.silver import build_silver_transformation_report
from src.transformation.gold import (
    build_dim_item, build_dim_supplier, build_dim_date, build_fact_purchase,
    load_dim_buyer_from_annual, save_gold_layer, validate_dim_buyer_grain,
)

t_inicio_total = time.time()

print("Carregando arquivo anual de item 2025 (4.7M linhas esperadas)...")
t0 = time.time()
caminho = local_parquet_path(2025, DATASET_ITEM)
df_ano = pd.read_parquet(caminho)
print(f"  {len(df_ano)} linhas, {time.time()-t0:.1f}s")
print()

print("Rodando Silver (ano inteiro)...")
t0 = time.time()
relatorio_silver, df_silver = build_silver_transformation_report(df_ano)
print(f"  {len(df_silver)} linhas apos Silver, {time.time()-t0:.1f}s")
print()

print("Carregando dim_buyer (2022-2026, 5 anos)...")
t0 = time.time()
dim_buyer = load_dim_buyer_from_annual([2022, 2023, 2024, 2025, 2026])
grao = validate_dim_buyer_grain(dim_buyer)
print(f"  {len(dim_buyer)} compradores, {time.time()-t0:.1f}s")
print(f"  grao valido: {grao['grao_valido']} (duplicados: {grao['id_compra_duplicado']})")
print()

print("Rodando build_dim_item (vetorizado)...")
t0 = time.time()
dim_item = build_dim_item(df_silver)
print(f"  {len(dim_item)} itens distintos, {time.time()-t0:.1f}s")
print()

print("Rodando build_dim_supplier (vetorizado)...")
t0 = time.time()
dim_supplier = build_dim_supplier(df_silver)
print(f"  {len(dim_supplier)} fornecedores distintos, {time.time()-t0:.1f}s")
print()

print("Rodando build_dim_date (2022-2026)...")
t0 = time.time()
from datetime import date
dim_date = build_dim_date(date(2022, 1, 1), date(2026, 12, 31))
print(f"  {len(dim_date)} linhas, {time.time()-t0:.1f}s")
print()

print("Montando fact_purchase...")
t0 = time.time()
fact, stats_fact = build_fact_purchase(df_silver, dim_buyer, dim_item)
print(f"  {len(fact)} linhas no fato, {time.time()-t0:.1f}s")
print(f"  excluidos sem resultado homologado: {stats_fact['n_excluidos_sem_resultado_homologado']}")
print(f"  sem match no buyer: {stats_fact['join_buyer']['linhas_sem_match_no_buyer']} ({stats_fact['join_buyer']['pct_sem_match']}%)")
print()

print("Persistindo Gold em Parquet...")
t0 = time.time()
stats_save = save_gold_layer(dim_buyer, dim_item, dim_supplier, dim_date, fact)
print(f"  {time.time()-t0:.1f}s")
print()

spend_total = fact["total_price"].sum()
print(f"TEMPO TOTAL DO PIPELINE: {time.time()-t_inicio_total:.1f}s")
print(f"Spend total (ano 2025, apenas transacoes homologadas): {spend_total:,.2f}")
