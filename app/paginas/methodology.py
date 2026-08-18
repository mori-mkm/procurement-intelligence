"""Pagina: methodology. Extraido de app/dashboard.py na Fase 15.5."""
import streamlit as st
import pandas as pd
import altair as alt

from app.helpers import (
    formatar_brl_compacto,
    formatar_inteiro,
    formatar_decimal,
    formatar_percentual,
    formatar_pp,
)


def render(dados):

    # ========================================================
    # ESCOPO
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Escopo do projeto'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Da aquisição dos dados públicos à geração de '
        'oportunidades acionáveis de Procurement.'
        '</div>',
        unsafe_allow_html=True,
    )

    scope_col1, scope_col2, scope_col3 = (
        st.columns(3)
    )

    with scope_col1:

        st.markdown(
            (
                '<div class="pi-method-card">'
                '<div class="pi-method-kicker">Fonte</div>'
                '<div class="pi-method-title">PNCP</div>'
                '<div class="pi-method-text">'
                'Dados públicos de compras utilizados para '
                'construir uma plataforma demonstrativa de '
                'Procurement Intelligence.'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with scope_col2:

        st.markdown(
            (
                '<div class="pi-method-card">'
                '<div class="pi-method-kicker">Objetivo</div>'
                '<div class="pi-method-title">'
                'Inteligência de Compras'
                '</div>'
                '<div class="pi-method-text">'
                'Combinar Spend Analytics, Supplier '
                'Concentration, Machine Learning e Savings '
                'Prioritization para apoiar investigação '
                'e tomada de decisão.'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with scope_col3:

        st.markdown(
            (
                '<div class="pi-method-card">'
                '<div class="pi-method-kicker">Uso</div>'
                '<div class="pi-method-title">'
                'Decision Support'
                '</div>'
                '<div class="pi-method-text">'
                'Os resultados priorizam onde investigar, '
                'negociar ou revisar. O sistema não determina '
                'automaticamente fraude ou sobrepreço.'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # ARQUITETURA
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Arquitetura de dados'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Separação entre ingestão, transformação, analytics '
        'e camada de apresentação.'
        '</div>',
        unsafe_allow_html=True,
    )

    arquitetura_html = (
        '<div class="pi-flow">'

        '<div class="pi-flow-step">'
        '<strong>PNCP</strong>'
        '<span>Fonte pública</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Bronze</strong>'
        '<span>Dados brutos</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Silver</strong>'
        '<span>Limpeza e regras</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Gold</strong>'
        '<span>Modelo analítico</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Analytics</strong>'
        '<span>Spend + ML + Savings</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Streamlit</strong>'
        '<span>Decision layer</span>'
        '</div>'

        '</div>'
    )

    st.markdown(
        arquitetura_html,
        unsafe_allow_html=True,
    )

    st.caption(
        "O dashboard consome artefatos previamente "
        "calculados e validados. Nenhum modelo é treinado "
        "durante a execução do Streamlit."
    )

    # ========================================================
    # VALIDACAO TEMPORAL
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-title">'
        'Validação temporal'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Separação cronológica para evitar seleção de modelo '
        'utilizando informação do período final de teste.'
        '</div>',
        unsafe_allow_html=True,
    )

    temporal_col1, temporal_col2, temporal_col3 = (
        st.columns(3)
    )

    with temporal_col1:

        st.markdown(
            (
                '<div class="pi-method-card">'
                '<div class="pi-method-kicker">2024</div>'
                '<div class="pi-method-title">'
                'Development Train'
                '</div>'
                '<div class="pi-method-text">'
                '<strong>46.143 transações</strong><br>'
                'Treinamento inicial dos modelos candidatos.'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with temporal_col2:

        st.markdown(
            (
                '<div class="pi-method-card">'
                '<div class="pi-method-kicker">2025</div>'
                '<div class="pi-method-title">'
                'Validation / Selection'
                '</div>'
                '<div class="pi-method-text">'
                '<strong>57.452 transações</strong><br>'
                'Seleção do algoritmo, bootstrap, tuning e '
                'calibração do threshold de anomalia.'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with temporal_col3:

        st.markdown(
            (
                '<div class="pi-method-card">'
                '<div class="pi-method-kicker">2026</div>'
                '<div class="pi-method-title">'
                'Final OOT Test'
                '</div>'
                '<div class="pi-method-text">'
                '<strong>24.692 transações</strong><br>'
                'Avaliação final do modelo congelado, '
                'sem nova seleção ou tuning.'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # MODEL SELECTION
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Model selection'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Comparação de diferentes famílias de modelos antes '
        'da escolha da solução final.'
        '</div>',
        unsafe_allow_html=True,
    )

    model_selection_df = pd.DataFrame(
        {
            "Modelo": [
                "Median Baseline",
                "Ridge",
                "CatBoost",
                "XGBoost",
                "LightGBM",
            ],
            "Papel": [
                "Benchmark simples",
                "Baseline linear regularizado",
                "Gradient boosting",
                "Gradient boosting",
                "Modelo selecionado",
            ],
            "Resultado": [
                "Referência",
                "Superado",
                "Superado",
                "Runner-up",
                "Selecionado",
            ],
        }
    )

    st.dataframe(
        model_selection_df,
        use_container_width=True,
        hide_index=True,
    )

    selection_col1, selection_col2 = (
        st.columns(2)
    )

    with selection_col1:

        st.markdown(
            (
                '<div class="pi-method-card">'
                '<div class="pi-method-kicker">'
                'Critério principal'
                '</div>'
                '<div class="pi-method-title">'
                'Performance Out-of-Time'
                '</div>'
                '<div class="pi-method-text">'
                'A escolha utilizou MAE em log no período '
                'de validação, complementado por métricas '
                'como RMSE, MedAPE e WAPE.'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with selection_col2:

        st.markdown(
            (
                '<div class="pi-method-card">'
                '<div class="pi-method-kicker">'
                'Incerteza'
                '</div>'
                '<div class="pi-method-title">'
                'Clustered Paired Bootstrap'
                '</div>'
                '<div class="pi-method-text">'
                'Os erros dos modelos foram comparados nas '
                'mesmas observações, com bootstrap agrupado '
                'por item_key.'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    st.info(
        "LightGBM e XGBoost ficaram estatisticamente "
        "indistinguíveis no bootstrap final de seleção. "
        "LightGBM foi mantido pelo menor MAE primário, "
        "melhor comportamento em unseen e integração "
        "já existente no pipeline."
    )

    st.caption(
        "O tuning posterior não produziu melhoria "
        "estatisticamente demonstrável; por parcimônia, "
        "a configuração LightGBM v0 foi preservada."
    )

    # ========================================================
    # OOT RESULT
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-title">'
        'Resultado final OOT 2026'
        '</div>',
        unsafe_allow_html=True,
    )

    oot_errors = dados["oot_errors"]

    oot_known_mask = (
        oot_errors["is_known_item"]
        .fillna(False)
        .astype(bool)
    )

    oot_mae = float(
        oot_errors[
            "abs_log_error"
        ].mean()
    )

    oot_known_mae = float(
        oot_errors.loc[
            oot_known_mask,
            "abs_log_error",
        ].mean()
    )

    oot_unseen_rate = float(
        100
        * (~oot_known_mask).mean()
    )

    oot_cols = st.columns(4)

    oot_cols[0].metric(
        "Observações",
        f"{len(oot_errors):,}".replace(",", "."),
    )

    oot_cols[1].metric(
        "MAE log",
        f"{oot_mae:.4f}".replace(".", ","),
    )

    oot_cols[2].metric(
        "Known MAE",
        f"{oot_known_mae:.4f}".replace(".", ","),
    )

    oot_cols[3].metric(
        "Unseen Rate",
        f"{oot_unseen_rate:.2f}%".replace(".", ","),
    )

    # ========================================================
    # ANOMALY -> SAVINGS
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-title">'
        'Da anomalia à oportunidade'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Uma anomalia estatística não se transforma '
        'automaticamente em Savings.'
        '</div>',
        unsafe_allow_html=True,
    )

    anomalies = dados["anomalies_2026"]

    threshold_values = (
        anomalies[
            "anomaly_threshold_abs_log"
        ]
        .dropna()
    )

    if not threshold_values.empty:
        anomaly_threshold = float(
            threshold_values.iloc[0]
        )
    else:
        anomaly_threshold = 0.0

    savings = dados["savings"]

    savings_high = savings[
        savings["confidence_tier"]
        == "Alta"
    ]

    savings_review = savings[
        savings["confidence_tier"]
        == "Revisao Alto Valor"
    ]

    opportunity_flow_html = (
        '<div class="pi-flow">'

        '<div class="pi-flow-step">'
        '<strong>Prediction</strong>'
        '<span>Preço esperado</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Anomaly</strong>'
        f'<span>|erro log| ≥ '
        f'{formatar_decimal(anomaly_threshold, 3)}</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Direction</strong>'
        '<span>Acima do esperado</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Quality Audit</strong>'
        '<span>Unidade + histórico + consistência</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Confidence Tier</strong>'
        '<span>Alta / Review / Baixa</span>'
        '</div>'

        '<div class="pi-flow-arrow">→</div>'

        '<div class="pi-flow-step">'
        '<strong>Procurement</strong>'
        '<span>Revisar ou negociar</span>'
        '</div>'

        '</div>'
    )

    st.markdown(
        opportunity_flow_html,
        unsafe_allow_html=True,
    )

    savings_cols = st.columns(4)

    savings_cols[0].metric(
        "High Confidence",
        f"{len(savings_high)}",
    )

    savings_cols[1].metric(
        "Potential Savings",
        formatar_brl_compacto(
            savings_high[
                "potential_saving"
            ].sum()
        ),
    )

    savings_cols[2].metric(
        "High-Value Review",
        f"{len(savings_review)}",
    )

    savings_cols[3].metric(
        "Value Under Review",
        formatar_brl_compacto(
            savings_review[
                "potential_saving"
            ].sum()
        ),
    )

    st.caption(
        "Potential Savings = max(preço observado − preço "
        "esperado, 0) × quantidade."
    )

    # ========================================================
    # LIMITACOES
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-title">'
        'Limitações e governança'
        '</div>',
        unsafe_allow_html=True,
    )

    limitation_col1, limitation_col2 = (
        st.columns(2)
    )

    with limitation_col1:

        st.markdown(
            (
                '<div class="pi-method-warning">'
                '<strong>Proxy de Procurement</strong><br>'
                'Os dados do PNCP representam compras '
                'públicas. Eles são utilizados para '
                'demonstrar técnicas aplicáveis a Procurement '
                'Intelligence e não representam processos '
                'ou dados reais de compras bancárias.'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with limitation_col2:

        st.markdown(
            (
                '<div class="pi-method-warning">'
                '<strong>Decision Support</strong><br>'
                'Anomalia estatística ou Potential Savings '
                'não constitui fraude, irregularidade, '
                'sobrepreço comprovado ou economia garantida. '
                'A decisão final exige revisão humana.'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # STACK
    # ========================================================

    with st.expander(
        "Stack técnica e componentes"
    ):

        stack_df = pd.DataFrame(
            {
                "Camada": [
                    "Data Engineering",
                    "Analytics",
                    "Machine Learning",
                    "Validation",
                    "Dashboard",
                    "Quality",
                ],
                "Tecnologias / Técnicas": [
                    "Python · ETL · Bronze / Silver / Gold",
                    "Pandas · Spend Analytics · HHI · ABC",
                    "LightGBM · XGBoost · CatBoost · Ridge",
                    "Temporal OOT · Clustered Bootstrap",
                    "Streamlit · Altair · CSS",
                    "Pytest · Data Quality · Audit Flags",
                ],
            }
        )

        st.dataframe(
            stack_df,
            use_container_width=True,
            hide_index=True,
        )
