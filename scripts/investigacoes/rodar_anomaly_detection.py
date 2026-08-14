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
from src.analytics.anomaly_detection import compute_residuals, flag_price_anomalies, summarize_anomalies

gold = load_gold_layer()
fact = gold["fact_purchase"]

df_prep = engineer_features(prepare_baseline_dataset(fact))
splits = split_temporal(df_prep)
treino, teste = align_categorical_dtypes(splits["treino"], splits["teste"])
modelo = train_lightgbm_model(treino)

teste_com_residuo = compute_residuals(teste, modelo)
teste_com_flag = flag_price_anomalies(teste_com_residuo, percentil=95)
resumo = summarize_anomalies(teste_com_flag)
print(json.dumps(resumo, ensure_ascii=False, indent=2))

print()
print("Top 10 maiores anomalias (acima do esperado):")
top = teste_com_flag[teste_com_flag["anomaly_direction"] == "acima_do_esperado"].nlargest(10, "residuo_log")
print(top[["item_key", "unit_price", "preco_esperado", "price_deviation_pct"]].to_string(index=False))
