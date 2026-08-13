import sys, time, gc
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
from src.transformation.gold import (
    build_dim_item, build_dim_supplier, build_dim_date, build_fact_purchase,
    load_dim_buyer_from_annual, save_gold_layer, validate_dim_buyer_grain,
    validate_fact_purchase_grain,
)
from datetime import date

t_inicio_total = time.time()

print("Carregando os 3 anos de item, cortando colunas nao usadas antes de concatenar...")
t0 = time.time()
frames = []
for ano in [2024, 2025, 2026]:
    caminho = local_parquet_path(ano, DATASET_ITEM)
    df_ano = pd.read_parquet(caminho)
    df_ano = select_necessary_columns(df_ano)
    print(f"  {ano}: {len(df_ano)} linhas, {len(df_ano.columns)} colunas")
    frames.append(df_ano)
    del df_ano

df_combinado = pd.concat(frames, ignore_index=True)
del frames
gc.collect()
print(f"Total combinado (ja com colunas cortadas): {len(df_combinado)} linhas, {len(df_combinado.columns)} colunas, {time.time()-t0:.1f}s")
print()

print("Rodando Silver UMA VEZ sobre os 3 anos combinados...")
t0 = time.time()
relatorio_silver, df_silver = build_silver_transformation_report(df_combinado)
del df_combinado
gc.collect()
print(f"  {len(df_silver)} linhas apos Silver, {time.time()-t0:.1f}s")
print(f"  duplicatas exatas removidas: {relatorio_silver['deduplicacao']['duplicatas_removidas']}")
print(f"  revisoes temporais resolvidas: {relatorio_silver['resolucao_revisoes_temporais']['revisoes_temporais_resolvidas']}")
print(f"  resultados conflitantes flagados: {relatorio_silver['resultado_conflitante']['n_linhas_flagadas']}")
print()

print("Carregando dim_buyer (2022-2026, ja materializado, reaproveitado)...")
t0 = time.time()
dim_buyer = load_dim_buyer_from_annual([2022, 2023, 2024, 2025, 2026])
grao_buyer = validate_dim_buyer_grain(dim_buyer)
print(f"  {len(dim_buyer)} compradores, {time.time()-t0:.1f}s, grao valido: {grao_buyer['grao_valido']}")
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
dim_date = build_dim_date(date(2022, 1, 1), date(2026, 12, 31))
print(f"  {len(dim_date)} linhas")
print()

print("Montando fact_purchase (2024-2026 combinado)...")
t0 = time.time()
fact, stats_fact = build_fact_purchase(df_silver, dim_buyer, dim_item)
del df_silver
gc.collect()
print(f"  {len(fact)} linhas no fato, {time.time()-t0:.1f}s")
print(f"  excluidos sem resultado homologado: {stats_fact['n_excluidos_sem_resultado_homologado']}")
print(f"  sem match no buyer: {stats_fact['join_buyer']['linhas_sem_match_no_buyer']} ({stats_fact['join_buyer']['pct_sem_match']}%)")
print()

print("Validando grao final do fact_purchase combinado...")
grao_fact = validate_fact_purchase_grain(fact)
print(f"  violacoes totais: {grao_fact['n_violacoes_totais']}")
print(f"  violacoes NAO flagadas (inesperadas): {grao_fact['n_grupos_violacao_nao_flagados']}")
print(f"  grao valido considerando flags: {grao_fact['grao_valido_considerando_flags']}")
print()

print("Persistindo Gold combinado em Parquet (sobrescreve versao so-2025)...")
t0 = time.time()
stats_save = save_gold_layer(dim_buyer, dim_item, dim_supplier, dim_date, fact)
print(f"  {time.time()-t0:.1f}s")
print()

spend_total = fact["total_price"].sum()
print(f"TEMPO TOTAL DO PIPELINE: {time.time()-t_inicio_total:.1f}s")
print(f"Spend total (2024-2026, apenas transacoes homologadas): {spend_total:,.2f}")

print()
print("Distribuicao de linhas por ano no fact_purchase final:")
print((fact["date_key"] // 10000).value_counts().sort_index())
