"""
Dashboard Streamlit - Procurement Intelligence Platform. Fase 11.
Le o Gold persistido (data/gold/) -- nao reprocessa pipeline em tempo real.
Roda: streamlit run app/dashboard.py
"""
import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

import streamlit as st
import pandas as pd

from src.transformation.gold import load_gold_layer
from src.analytics.spend_analytics import compute_spend_by_category, compute_hhi_by_category, build_supplier_abc_curve
from src.analytics.price_baseline import prepare_baseline_dataset, split_temporal, compute_median_baseline, evaluate_baseline
from src.analytics.price_ml import engineer_features, align_categorical_dtypes, train_lightgbm_model
from src.analytics.anomaly_detection import compute_residuals, flag_price_anomalies, summarize_anomalies
from src.analytics.savings_engine import compute_savings_opportunity, rank_savings_by_category, summarize_savings

st.set_page_config(page_title="Procurement Intelligence", layout="wide")


@st.cache_resource
def carregar_tudo():
    """Carrega Gold, treina modelo, calcula tudo -- uma vez, cacheado.
    Nao reprocessa a cada interacao do usuario."""
    gold = load_gold_layer()
    fact = gold["fact_purchase"]

    df_prep = engineer_features(prepare_baseline_dataset(fact))
    splits = split_temporal(df_prep)
    baseline = compute_median_baseline(splits["treino"])
    treino, teste = align_categorical_dtypes(splits["treino"], splits["teste"])
    modelo = train_lightgbm_model(treino)

    teste_residuo = compute_residuals(teste, modelo)
    teste_flag = flag_price_anomalies(teste_residuo, percentil=95)
    savings = compute_savings_opportunity(teste_flag)

    return {
        "fact": fact,
        "df_prep": df_prep,
        "baseline": baseline,
        "modelo": modelo,
        "features": treino.columns,
        "teste_flag": teste_flag,
        "savings": savings,
    }


dados = carregar_tudo()

st.title("Procurement Intelligence Platform")
st.caption(
    "Dados públicos do PNCP (compras.gov.br) como proxy para procurement corporativo. "
    "Ver docs/adr/ para limitações metodológicas detalhadas."
)

aba_spend, aba_preco, aba_anomalias, aba_consulta = st.tabs(
    ["Spend Intelligence", "Price Baseline", "Anomalias & Savings", "Consulta de Item"]
)

with aba_spend:
    st.header("Spend por categoria relevante")
    spend_cat = compute_spend_by_category(dados["fact"])
    st.dataframe(spend_cat, use_container_width=True)

    st.header("Concentração de fornecedor (HHI)")
    hhi_cat = compute_hhi_by_category(dados["fact"])
    st.dataframe(hhi_cat, use_container_width=True)

    categoria_abc = st.selectbox(
        "Ver Curva ABC de fornecedores para:",
        [c for c in spend_cat["categoria_relevante"] if c != "Não categorizado"],
    )
    if categoria_abc:
        abc = build_supplier_abc_curve(dados["fact"], category=categoria_abc)
        st.bar_chart(abc.head(20).set_index("supplier_key")["share_pct"])
        st.dataframe(abc.head(20), use_container_width=True)

with aba_preco:
    st.header("Baseline de preço (mediana) vs. Modelo ML (LightGBM)")
    splits = split_temporal(dados["df_prep"])
    resultado_baseline = evaluate_baseline(splits["teste"], dados["baseline"])
    st.metric("Cobertura do Baseline (mediana)", f"{resultado_baseline['pct_cobertura']}%")
    st.metric("MAPE mediana (Baseline)", f"{resultado_baseline['mape_mediana']}%")
    st.metric("Cobertura do Modelo ML", "100%")
    st.caption("Ver ADR-0015 e nota da Fase 8 (docs/adr/) para discussão de por que o ganho do ML sobre o baseline é limitado neste dataset.")

with aba_anomalias:
    st.header("Anomalias de preço e Savings Opportunity")
    resumo_anom = summarize_anomalies(dados["teste_flag"])
    resumo_sav = summarize_savings(dados["savings"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Anomalias detectadas", resumo_anom["n_anomalias"])
    col2.metric("Savings potencial (bruto)", f"R$ {resumo_sav['savings_potencial_total']:,.0f}")
    col3.metric("Savings potencial (sem ticket alto)", f"R$ {resumo_sav['savings_potencial_excluindo_ticket_alto']:,.0f}")

    st.warning(
        "Rótulo 'Potential Savings Opportunity', não 'sobrepreço confirmado' — "
        "requer revisão humana antes de qualquer ação (ver Fase 0, princípios metodológicos)."
    )

    ranking = rank_savings_by_category(dados["savings"])
    st.dataframe(ranking, use_container_width=True)

    st.subheader("Top 20 oportunidades (excluindo ticket alto — maior confiança)")
    confiaveis = dados["savings"][~dados["savings"]["ticket_alto_cautela"]]
    st.dataframe(
        confiaveis.nlargest(20, "potential_saving")[
            ["item_key", "unit_price", "preco_esperado", "quantity", "potential_saving"]
        ],
        use_container_width=True,
    )

with aba_consulta:
    st.header("Consulta de preço esperado por item")
    itens_disponiveis = sorted(dados["baseline"]["item_key"].unique())
    item_selecionado = st.selectbox("Escolha um item:", itens_disponiveis)

    if item_selecionado:
        linha_baseline = dados["baseline"][dados["baseline"]["item_key"] == item_selecionado]
        st.write(f"**Preço esperado (mediana, treino 2024):** R$ {linha_baseline['preco_esperado'].iloc[0]:,.2f}")
        st.write(f"**Transações no treino:** {linha_baseline['n_transacoes_treino'].iloc[0]}")
        st.write(f"**Baseline confiável:** {'Sim' if linha_baseline['baseline_confiavel'].iloc[0] else 'Não (poucas transações)'}")

        exemplo = dados["df_prep"][dados["df_prep"]["item_key"] == item_selecionado].head(1)
        if not exemplo.empty:
            entrada = exemplo[dados["features"]]
            contrib = dados["modelo"].booster_.predict(entrada, pred_contrib=True)
            nomes = list(dados["features"]) + ["base_value"]
            st.subheader("Explicabilidade (SHAP) — contribuição por fator, em escala log(preço)")
            shap_df = pd.DataFrame({"fator": nomes, "contribuicao": contrib[0]})
            st.bar_chart(shap_df.set_index("fator")["contribuicao"])
