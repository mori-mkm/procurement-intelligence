"""
Fase 15.3 (extensao) - Gera artefato compacto de Curva ABC de fornecedores
por categoria, incluindo visao global. Elimina a dependencia do Gold
completo nas paginas Executive Overview e Spend & Suppliers.
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

import pandas as pd

from src.transformation.gold import load_gold_layer
from src.analytics.spend_analytics import build_supplier_abc_curve

GLOBAL_LABEL = "__GLOBAL__"
DESTINO = RAIZ / "data" / "model_validation" / "supplier_abc_by_category.parquet"


def main():
    print("Carregando Gold local (fact_purchase, dim_supplier)...")
    gold = load_gold_layer()
    fact = gold["fact_purchase"]
    dim_supplier = gold["dim_supplier"][["supplier_key", "nome_fornecedor"]].drop_duplicates("supplier_key")

    fact_relevante = fact[fact["categoria_relevante"].notna()].copy()
    print(f"  {len(fact_relevante)} linhas em categorias relevantes")

    categorias = sorted(fact_relevante["categoria_relevante"].unique())
    print(f"  {len(categorias)} categorias: {categorias}")

    blocos = []

    print("Calculando Curva ABC global...")
    abc_global = build_supplier_abc_curve(fact_relevante)
    abc_global["categoria_relevante"] = GLOBAL_LABEL
    blocos.append(abc_global)

    for cat in categorias:
        print(f"Calculando Curva ABC para: {cat}...")
        abc_cat = build_supplier_abc_curve(fact_relevante, category=cat)
        abc_cat["categoria_relevante"] = cat
        blocos.append(abc_cat)

    resultado = pd.concat(blocos, ignore_index=True)

    resultado["supplier_key"] = resultado["supplier_key"].astype("string")
    dim_supplier["supplier_key"] = dim_supplier["supplier_key"].astype("string")
    resultado = resultado.merge(dim_supplier, on="supplier_key", how="left", validate="many_to_one")
    resultado["nome_fornecedor"] = resultado["nome_fornecedor"].fillna(resultado["supplier_key"])

    resultado.to_parquet(DESTINO, index=False)
    print(f"Salvo em {DESTINO} ({len(resultado)} linhas, {DESTINO.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
