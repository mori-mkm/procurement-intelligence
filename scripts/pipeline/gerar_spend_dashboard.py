"""
Fase 15.3 - Gera artefatos compactos de Spend/HHI para o dashboard.
Roda uma vez sobre o Gold local (nao versionado) e salva resultado
pequeno em data/model_validation/, seguindo o mesmo padrao dos demais
artefatos oficiais consumidos por dashboard_data.py.
"""
import sys
from pathlib import Path


def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")


RAIZ = achar_raiz_projeto(Path(__file__))
sys.path.insert(0, str(RAIZ))

from src.transformation.gold import load_gold_layer
from src.analytics.spend_analytics import compute_spend_by_category, compute_hhi_by_category

DESTINO = RAIZ / "data" / "model_validation"


def main():
    print("Carregando Gold local (fact_purchase)...")
    gold = load_gold_layer()
    fact = gold["fact_purchase"]
    print(f"  {len(fact)} linhas totais")

    fact_relevante = fact[fact["categoria_relevante"].notna()].copy()
    print(f"  {len(fact_relevante)} linhas em categorias relevantes (exclui Nao categorizado)")

    print("Calculando spend_by_category...")
    spend = compute_spend_by_category(fact_relevante)
    caminho_spend = DESTINO / "spend_by_category.parquet"
    spend.to_parquet(caminho_spend, index=False)
    print(f"  Salvo em {caminho_spend} ({len(spend)} categorias)")

    print("Calculando hhi_by_category...")
    hhi = compute_hhi_by_category(fact_relevante)
    caminho_hhi = DESTINO / "hhi_by_category.parquet"
    hhi.to_parquet(caminho_hhi, index=False)
    print(f"  Salvo em {caminho_hhi} ({len(hhi)} categorias)")


if __name__ == "__main__":
    main()
