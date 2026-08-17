import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

import json
from src.transformation.gold import load_gold_layer
from src.analytics.price_baseline import prepare_baseline_dataset, split_temporal
from src.analytics.price_ml import engineer_features, align_categorical_dtypes, train_lightgbm_model
from src.analytics.anomaly_detection import compute_residuals, flag_price_anomalies
from src.analytics.savings_engine import compute_savings_opportunity, rank_savings_by_category, summarize_savings

gold = load_gold_layer()
fact = gold["fact_purchase"]

df_prep = engineer_features(prepare_baseline_dataset(fact))
splits = split_temporal(df_prep)
treino, teste = align_categorical_dtypes(splits["treino"], splits["teste"])
modelo = train_lightgbm_model(treino)

teste_residuo = compute_residuals(teste, modelo)
teste_flag = flag_price_anomalies(teste_residuo, percentil=95)

savings = compute_savings_opportunity(teste_flag)
resumo = summarize_savings(savings)
ranking = rank_savings_by_category(savings)

print("=== Resumo geral ===")
print(json.dumps(resumo, ensure_ascii=False, indent=2))
print()
print("=== Ranking por categoria ===")
print(ranking.to_string(index=False))
print()
print("=== Top 10 oportunidades, EXCLUINDO ticket alto (mais confiaveis) ===")
confiaveis = savings[~savings["ticket_alto_cautela"]]
print(confiaveis.nlargest(10, "potential_saving")[["item_key", "unit_price", "preco_esperado", "quantity", "potential_saving"]].to_string(index=False))
