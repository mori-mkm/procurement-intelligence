import sys, time
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

import duckdb
from src.ingestion.pncp_bulk_annual import local_parquet_path, DATASET_ITEM
from src.transformation.silver import build_silver_transformation_report
from src.transformation.gold import build_dim_item, build_dim_supplier, build_fact_purchase, load_dim_buyer_from_annual

caminho = local_parquet_path(2025, DATASET_ITEM)
con = duckdb.connect()

print("Fatiando dezembro/2025 do arquivo anual...")
t0 = time.time()
df_mes = con.execute(f"""
    SELECT * FROM read_parquet('{caminho.as_posix()}')
    WHERE data_resultado >= '2025-12-01' AND data_resultado <= '2025-12-31'
""").df()
print(f"  {len(df_mes)} linhas, {time.time()-t0:.1f}s")
print()

print("Rodando Silver...")
t0 = time.time()
relatorio_silver, df_silver = build_silver_transformation_report(df_mes)
print(f"  {len(df_silver)} linhas apos Silver, {time.time()-t0:.1f}s")
print()

print("Carregando dim_buyer (ja materializado)...")
t0 = time.time()
dim_buyer = load_dim_buyer_from_annual([2024, 2025, 2026])
print(f"  {time.time()-t0:.1f}s")
print()

print("Rodando build_dim_item (loop nao-vetorizado -- ponto de atencao)...")
t0 = time.time()
dim_item = build_dim_item(df_silver)
print(f"  {len(dim_item)} itens distintos, {time.time()-t0:.1f}s")
print()

print("Rodando build_dim_supplier...")
t0 = time.time()
dim_supplier = build_dim_supplier(df_silver)
print(f"  {len(dim_supplier)} fornecedores distintos, {time.time()-t0:.1f}s")
print()

print("Montando fact_purchase...")
t0 = time.time()
fact, stats = build_fact_purchase(df_silver, dim_buyer, dim_item)
print(f"  {len(fact)} linhas no fato, {time.time()-t0:.1f}s")
print()

print("Spend total do mes:", fact["total_price"].sum())
