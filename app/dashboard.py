"""
Dashboard Streamlit - Procurement Intelligence Platform.

Fase 14:
O dashboard consome artefatos analiticos previamente
calculados e validados.

Nao treina modelos, nao calibra thresholds e nao
recalcula savings durante a execucao.
"""

import sys
from pathlib import Path
from textwrap import dedent


def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()

    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai

    raise RuntimeError("Nao encontrei a raiz do projeto")


RAIZ = achar_raiz_projeto(Path(__file__))
sys.path.insert(0, str(RAIZ))


import altair as alt
import pandas as pd
import streamlit as st

from src.transformation.gold import load_gold_layer
from src.analytics.spend_analytics import (
    compute_spend_by_category,
    compute_hhi_by_category,
    build_supplier_abc_curve,
)
from src.analytics.dashboard_data import (
    load_dashboard_artifacts,
)


st.set_page_config(
    page_title="Procurement Intelligence",
    page_icon=None,
    layout="wide",
)


def aplicar_design_system():
    st.markdown(
        """
        <style>
        :root {
            --red: #CC092F;
            --wine: #5B0011;
            --blue: #2B6CB0;
            --green: #1E874B;
            --amber: #C9851A;

            --bg: #F1F1F4;
            --card: #FFFFFF;
            --ink: #1F2024;
            --muted: #7A7D85;
            --line: #E9E9EE;
            --soft: #F7F7F9;

            --red-soft: #FDEAEE;
            --green-soft: #E7F5EC;
            --amber-soft: #FDF3E2;

            --radius-card: 14px;
            --radius-control: 8px;
            --shadow: 0 4px 14px rgba(20,20,40,.05);
        }

        html,
        body,
        [class*="css"] {
            font-family:
                "Segoe UI",
                Roboto,
                Helvetica,
                Arial,
                sans-serif;
        }

        /* --------------------------------------------------
           APP
        -------------------------------------------------- */

        [data-testid="stAppViewContainer"] {
            background: var(--bg);
            color: var(--ink);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1500px;
            padding-top: 1.25rem;
            padding-left: 1.6rem;
            padding-right: 1.6rem;
            padding-bottom: 2rem;
        }

        /* --------------------------------------------------
           SIDEBAR
        -------------------------------------------------- */

        [data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0;
        }

        .pi-brand {
            margin: 0 -1rem 1rem -1rem;
            padding: 20px 18px 18px 18px;
            background:
                linear-gradient(
                    135deg,
                    #CC092F,
                    #5B0011
                );
            color: #FFFFFF;
        }

        .pi-brand-title {
            margin: 0;
            font-size: 1.05rem;
            font-weight: 800;
            letter-spacing: -0.01em;
        }

        .pi-brand-subtitle {
            margin-top: 4px;
            font-size: .72rem;
            opacity: .82;
        }

        .pi-sidebar-label {
            margin-top: 18px;
            margin-bottom: 7px;
            color: var(--red);
            font-size: .70rem;
            font-weight: 700;
            letter-spacing: .13em;
            text-transform: uppercase;
        }

        [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 3px;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: 8px 9px;
            border-radius: 9px;
            transition: background .2s ease;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: var(--soft);
        }

        [data-testid="stSidebar"]
        [role="radiogroup"]
        label:has(input:checked) {
            background: var(--red-soft);
        }

        [data-testid="stSidebar"]
        [role="radiogroup"]
        label:has(input:checked) p {
            color: var(--red);
            font-weight: 700;
        }

        /* --------------------------------------------------
           PAGE HEADER
        -------------------------------------------------- */

        .pi-page-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            margin-bottom: 18px;
        }

        .pi-page-title {
            margin: 0;
            color: var(--ink);
            font-size: 1.50rem;
            font-weight: 800;
            line-height: 1.2;
            letter-spacing: -0.02em;
        }

        .pi-page-subtitle {
            margin-top: 5px;
            color: var(--muted);
            font-size: .88rem;
            line-height: 1.45;
        }

        .pi-data-badge {
            white-space: nowrap;
            background: #FFFFFF;
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 6px 10px;
            color: var(--muted);
            font-size: .72rem;
        }

        /* --------------------------------------------------
           TITULOS
        -------------------------------------------------- */

        h1 {
            font-size: 1.50rem !important;
            font-weight: 800 !important;
        }

        h2 {
            font-size: 1.14rem !important;
            font-weight: 800 !important;
        }

        h3 {
            font-size: 1.04rem !important;
            font-weight: 700 !important;
        }

        /* --------------------------------------------------
           KPI CARDS
        -------------------------------------------------- */

        [data-testid="stMetric"] {
            background: var(--card);
            border-radius: var(--radius-card);
            padding: 14px 16px;
            box-shadow: var(--shadow);
            border: 1px solid rgba(233,233,238,.65);
            min-height: 108px;
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted);
            font-size: .78rem;
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: var(--wine);
            font-size: 1.75rem;
            font-weight: 800;
            font-variant-numeric: tabular-nums;
        }

        /* --------------------------------------------------
           CONTAINERS
        -------------------------------------------------- */

        [data-testid="stDataFrame"],
        [data-testid="stPlotlyChart"],
        [data-testid="stVegaLiteChart"] {
            background: var(--card);
            border-radius: var(--radius-card);
        }

        hr {
            border-color: var(--line);
        }

        /* --------------------------------------------------
           CONTROLS
        -------------------------------------------------- */

        [data-baseweb="select"] > div {
            border-radius: var(--radius-control);
        }

        .stButton > button {
            border-radius: 10px;
            font-weight: 700;
        }

        /* --------------------------------------------------
           EXECUTIVE OVERVIEW
        -------------------------------------------------- */

        .pi-section-title {
            margin: 4px 0 4px 0;
            color: var(--ink);
            font-size: 1.04rem;
            font-weight: 800;
        }

        .pi-section-subtitle {
            margin: 0 0 12px 0;
            color: var(--muted);
            font-size: .78rem;
        }

        .pi-insight {
            background: #FFFFFF;
            border-radius: var(--radius-card);
            padding: 16px 18px;
            box-shadow: var(--shadow);
            border-left: 4px solid var(--wine);
            line-height: 1.55;
            font-size: .86rem;
        }

        .pi-insight-title {
            color: var(--wine);
            font-weight: 800;
            margin-bottom: 7px;
        }

        .pi-insight p {
            margin: 0 0 7px 0;
        }

        .pi-insight p:last-child {
            margin-bottom: 0;
        }

        .pi-monitoring-note {
            margin-top: 12px;
            background: var(--amber-soft);
            border-left: 4px solid var(--amber);
            border-radius: 11px;
            padding: 11px 14px;
            color: var(--ink);
            font-size: .80rem;
            line-height: 1.45;
        }

        /* --------------------------------------------------
           METHODOLOGY
        -------------------------------------------------- */

        .pi-method-card {
            background: #FFFFFF;
            border-radius: var(--radius-card);
            padding: 15px 17px;
            box-shadow: var(--shadow);
            border: 1px solid rgba(233,233,238,.75);
            height: 100%;
        }

        .pi-method-kicker {
            color: var(--red);
            font-size: .68rem;
            font-weight: 800;
            letter-spacing: .11em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }

        .pi-method-title {
            color: var(--ink);
            font-size: .98rem;
            font-weight: 800;
            margin-bottom: 5px;
        }

        .pi-method-text {
            color: var(--muted);
            font-size: .80rem;
            line-height: 1.48;
        }

        .pi-flow {
            display: flex;
            align-items: stretch;
            gap: 7px;
            width: 100%;
            margin: 10px 0 18px 0;
        }

        .pi-flow-step {
            flex: 1;
            background: #FFFFFF;
            border: 1px solid var(--line);
            border-radius: 11px;
            padding: 12px 8px;
            text-align: center;
            box-shadow: var(--shadow);
        }

        .pi-flow-step strong {
            display: block;
            color: var(--wine);
            font-size: .82rem;
            margin-bottom: 3px;
        }

        .pi-flow-step span {
            color: var(--muted);
            font-size: .68rem;
        }

        .pi-flow-arrow {
            display: flex;
            align-items: center;
            color: var(--graph-muted);
            font-size: 1rem;
        }

        .pi-method-warning {
            background: var(--amber-soft);
            border-left: 4px solid var(--amber);
            border-radius: 11px;
            padding: 13px 15px;
            color: var(--ink);
            font-size: .81rem;
            line-height: 1.5;
        }

        @media (max-width: 900px) {
            .pi-flow {
                flex-direction: column;
            }

            .pi-flow-arrow {
                justify-content: center;
                transform: rotate(90deg);
            }
        }

        /* --------------------------------------------------
        ALERTS / EXPANDERS
        -------------------------------------------------- */

        [data-testid="stAlert"] {
            border-radius: 11px;
            font-size: .82rem;
        }

        [data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid var(--line);
            border-radius: var(--radius-card);
            box-shadow: var(--shadow);
        }

        [data-testid="stExpander"] summary {
            font-weight: 700;
            color: var(--ink);
        }

        /* --------------------------------------------------
           RESPONSIVE
        -------------------------------------------------- */

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .pi-page-header {
                flex-direction: column;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


aplicar_design_system()


def formatar_brl_compacto(valor: float) -> str:
    valor = float(valor)

    if abs(valor) >= 1_000_000_000:
        numero = valor / 1_000_000_000
        return (
            f"R$ {numero:.1f} bi"
            .replace(".", ",")
        )

    if abs(valor) >= 1_000_000:
        numero = valor / 1_000_000
        return (
            f"R$ {numero:.1f} mi"
            .replace(".", ",")
        )

    if abs(valor) >= 1_000:
        numero = valor / 1_000
        return (
            f"R$ {numero:.1f} mil"
            .replace(".", ",")
        )

    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatar_inteiro(valor) -> str:
    return (
        f"{int(valor):,}"
        .replace(",", ".")
    )


def formatar_decimal(
    valor,
    casas: int = 2,
) -> str:
    return (
        f"{float(valor):.{casas}f}"
        .replace(".", ",")
    )


def formatar_percentual(
    valor,
    casas: int = 2,
    sinal: bool = False,
) -> str:

    if sinal:
        texto = (
            f"{float(valor):+.{casas}f}"
        )
    else:
        texto = (
            f"{float(valor):.{casas}f}"
        )

    return (
        texto.replace(".", ",")
        + "%"
    )


def formatar_pp(
    valor,
    casas: int = 2,
    sinal: bool = True,
) -> str:

    if sinal:
        texto = (
            f"{float(valor):+.{casas}f}"
        )
    else:
        texto = (
            f"{float(valor):.{casas}f}"
        )

    return (
        texto.replace(".", ",")
        + " p.p."
    )


@st.cache_data(show_spinner=False)
def carregar_dados_dashboard():
    """
    Carrega somente dados persistidos.

    Gold:
        usada para Spend Intelligence.

    Model Validation:
        artefatos oficiais produzidos pela Fase 13.
    """

    gold = load_gold_layer()

    artifacts = load_dashboard_artifacts(
        RAIZ
    )

    return {
    "fact": gold["fact_purchase"],
    "dim_supplier": gold["dim_supplier"],
    **artifacts,
    }


dados = carregar_dados_dashboard()


# ============================================================
# SIDEBAR / NAVEGACAO
# ============================================================

with st.sidebar:

    st.markdown(
    dedent(
        """
        <div class="pi-brand">
            <div class="pi-brand-title">
                Procurement Intelligence
            </div>
            <div class="pi-brand-subtitle">
                Analytics Platform
            </div>
        </div>
        """
    ),
    unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-sidebar-label">Navegação</div>',
        unsafe_allow_html=True,
    )

    pagina = st.radio(
        "Navegação",
        [
            "Executive Overview",
            "Spend & Suppliers",
            "Price Intelligence",
            "Savings Opportunities",
            "Model Monitoring",
            "Methodology",
        ],
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="pi-sidebar-label">Fonte</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "PNCP — dados públicos utilizados como proxy "
        "para Procurement Intelligence."
    )

    st.caption(
        "Desenvolvimento: 2024 · "
        "Validação: 2025 · "
        "OOT: 2026"
    )


PAGE_INFO = {
    "Executive Overview": (
        "Executive Overview",
        "Visão consolidada de spend, concentração, "
        "desvios de preço e oportunidades financeiras.",
    ),

    "Spend & Suppliers": (
        "Spend & Suppliers",
        "Onde o dinheiro está sendo gasto e onde existe "
        "concentração de fornecedores.",
    ),

    "Price Intelligence": (
        "Price Intelligence",
        "Monitoramento de preços observados versus "
        "valores esperados pelo modelo.",
    ),

    "Savings Opportunities": (
        "Savings Opportunities",
        "Oportunidades financeiras priorizadas por "
        "impacto e confiabilidade.",
    ),

    "Model Monitoring": (
        "Model Monitoring",
        "Estabilidade temporal, cold start, drift e "
        "performance out-of-time.",
    ),

    "Methodology": (
        "Methodology",
        "Arquitetura, validação temporal, modelos e "
        "regras metodológicas do projeto.",
    ),
}


titulo_pagina, subtitulo_pagina = PAGE_INFO[
    pagina
]


st.markdown(
    dedent(
        f"""
        <div class="pi-page-header">
            <div>
                <h1 class="pi-page-title">{titulo_pagina}</h1>
                <div class="pi-page-subtitle">
                    {subtitulo_pagina}
                </div>
            </div>
            <div class="pi-data-badge">
                PNCP · OOT 2026
            </div>
        </div>
        """
    ),
    unsafe_allow_html=True,
)


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if pagina == "Executive Overview":

    # ========================================================
    # BASE EXECUTIVA
    # ========================================================

    fact_relevante = dados["fact"][
        dados["fact"]["categoria_relevante"]
        .notna()
    ].copy()

    spend_relevante = compute_spend_by_category(
        fact_relevante
    )

    hhi_relevante = compute_hhi_by_category(
        fact_relevante
    )

    fornecedores_relevantes = (
        build_supplier_abc_curve(
            fact_relevante
        )
    )

    savings = dados["savings"]

    savings_alta = savings[
        savings["confidence_tier"]
        == "Alta"
    ].copy()

    savings_revisao = savings[
        savings["confidence_tier"]
        == "Revisao Alto Valor"
    ].copy()

    anomalies = dados["anomalies_2026"]

    errors = dados["oot_errors"]

    # ========================================================
    # KPIs
    # ========================================================

    spend_monitorado = float(
        spend_relevante[
            "spend_total"
        ].sum()
    )

    n_fornecedores = int(
        len(fornecedores_relevantes)
    )

    potential_high_confidence = float(
        savings_alta[
            "potential_saving"
        ].sum()
    )

    potential_review = float(
        savings_revisao[
            "potential_saving"
        ].sum()
    )

    n_anomalias_acima = int(
        (
            anomalies[
                "anomaly_direction"
            ]
            == "acima_do_esperado"
        ).sum()
    )

    n_concentradas = int(
        (
            hhi_relevante[
                "classificacao_hhi"
            ]
            == "altamente concentrado"
        ).sum()
    )

    known_mask = (
        errors["is_known_item"]
        .fillna(False)
        .astype(bool)
    )

    unseen_rate = (
        100
        * (~known_mask).mean()
    )

    # ========================================================
    # KPI CARDS
    # ========================================================

    cols = st.columns(6)

    cols[0].metric(
        "Spend Monitorado",
        formatar_brl_compacto(
            spend_monitorado
        ),
    )

    cols[1].metric(
        "Fornecedores Monitorados",
        f"{n_fornecedores:,}"
        .replace(",", "."),
    )

    cols[2].metric(
        "Potential Savings — Alta Confiança",
        formatar_brl_compacto(
            potential_high_confidence
        ),
    )

    cols[3].metric(
        "Alto Valor em Revisão",
        formatar_brl_compacto(
            potential_review
        ),
    )

    cols[4].metric(
        "Anomalias Acima do Esperado",
        f"{n_anomalias_acima:,}"
        .replace(",", "."),
    )

    cols[5].metric(
        "Categorias com Alta Concentração",
        f"{n_concentradas}",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================================
    # DADOS PARA LEITURA EXECUTIVA
    # ========================================================

    top_categoria = (
        spend_relevante
        .sort_values(
            "spend_total",
            ascending=False,
        )
        .iloc[0]
    )

    top_categoria_nome = (
        top_categoria[
            "categoria_relevante"
        ]
    )

    top_categoria_share = float(
        top_categoria[
            "spend_total"
        ]
        / spend_monitorado
        * 100
    )

    if not savings_alta.empty:

        savings_categoria = (
            savings_alta
            .groupby(
                "categoria_relevante",
                dropna=False,
            )["potential_saving"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        top_savings_categoria = (
            savings_categoria.index[0]
        )

        top_savings_valor = float(
            savings_categoria.iloc[0]
        )

    else:

        top_savings_categoria = (
            "Sem oportunidades"
        )

        top_savings_valor = 0.0

    hhi_top = (
        hhi_relevante
        .sort_values(
            "hhi",
            ascending=False,
        )
        .iloc[0]
    )

    # ========================================================
    # LEITURA EXECUTIVA
    # ========================================================

    top_categoria_share_fmt = (
        f"{top_categoria_share:.1f}"
        .replace(".", ",")
    )

    hhi_top_fmt = (
        f"{hhi_top['hhi']:,.0f}"
        .replace(",", ".")
    )

    st.markdown(
        dedent(
            f"""
            <div class="pi-insight">
                <div class="pi-insight-title">Leitura executiva</div>
                <p>
                    <strong>{top_categoria_nome}</strong> concentra
                    <strong>{top_categoria_share_fmt}%</strong>
                    do spend monitorado.
                </p>
                <p>
                    Foram identificados
                    <strong>{formatar_brl_compacto(potential_high_confidence)}</strong>
                    em oportunidades de alta confiança.
                </p>
                <p>
                    A principal categoria em impacto potencial é
                    <strong>{top_savings_categoria}</strong>,
                    com
                    <strong>{formatar_brl_compacto(top_savings_valor)}</strong>.
                </p>
                <p>
                    A maior concentração de fornecedores ocorre em
                    <strong>{hhi_top["categoria_relevante"]}</strong>,
                    com HHI de
                    <strong>{hhi_top_fmt}</strong>.
                </p>
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    # ========================================================
    # GRAFICOS
    # ========================================================

    grafico_esquerda, grafico_direita = (
        st.columns(2)
    )

    # --------------------------------------------------------
    # Spend por categoria
    # --------------------------------------------------------

    with grafico_esquerda:

        st.markdown(
            '<div class="pi-section-title">'
            'Spend por categoria'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="pi-section-subtitle">'
            'Distribuição do spend nas categorias '
            'monitoradas.'
            '</div>',
            unsafe_allow_html=True,
        )

        chart_spend_df = (
            spend_relevante
            .sort_values(
                "spend_total",
                ascending=False,
            )
            .copy()
        )

        chart_spend_df[
            "spend_formatado"
        ] = (
            chart_spend_df[
                "spend_total"
            ]
            .apply(
                formatar_brl_compacto
            )
        )

        chart_spend_df[
            "share_formatado"
        ] = (
            chart_spend_df[
                "spend_total"
            ]
            / spend_monitorado
            * 100
        ).map(
            lambda x:
                f"{x:.1f}%"
        )

        chart_spend = (
            alt.Chart(
                chart_spend_df
            )
            .mark_bar(
                color="#5B0011",
                cornerRadiusEnd=4,
            )
            .encode(
                x=alt.X(
                    "spend_total:Q",
                    title=None,
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                        labels=False,
                        ticks=False,
                        domain=False,
                    ),
                ),

                y=alt.Y(
                    "categoria_relevante:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelColor="#7A7D85",
                        labelLimit=180,
                        domain=False,
                        ticks=False,
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "categoria_relevante:N",
                        title="Categoria",
                    ),
                    alt.Tooltip(
                        "spend_formatado:N",
                        title="Spend",
                    ),
                    alt.Tooltip(
                        "share_formatado:N",
                        title="Participação",
                    ),
                ],
            )
            .properties(
                height=280
            )
        )

        st.altair_chart(
            chart_spend,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Savings por categoria / confianca
    # --------------------------------------------------------

    with grafico_direita:

        st.markdown(
            '<div class="pi-section-title">'
            'Savings por categoria'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="pi-section-subtitle">'
            'Alta confiança versus oportunidades '
            'de alto valor em revisão.'
            '</div>',
            unsafe_allow_html=True,
        )

        savings_chart_df = (
            savings[
                savings[
                    "confidence_tier"
                ].isin(
                    [
                        "Alta",
                        "Revisao Alto Valor",
                    ]
                )
            ]
            .groupby(
                [
                    "categoria_relevante",
                    "confidence_tier",
                ],
                dropna=False,
            )[
                "potential_saving"
            ]
            .sum()
            .reset_index()
        )

        savings_chart_df[
            "valor_formatado"
        ] = (
            savings_chart_df[
                "potential_saving"
            ]
            .apply(
                formatar_brl_compacto
            )
        )

        chart_savings = (
            alt.Chart(
                savings_chart_df
            )
            .mark_bar(
                cornerRadiusEnd=3
            )
            .encode(
                x=alt.X(
                    "potential_saving:Q",
                    title=None,
                    axis=alt.Axis(
                        labels=False,
                        ticks=False,
                        domain=False,
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                y=alt.Y(
                    "categoria_relevante:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelColor="#7A7D85",
                        labelLimit=180,
                        domain=False,
                        ticks=False,
                    ),
                ),

                color=alt.Color(
                    "confidence_tier:N",
                    title="Confiança",
                    scale=alt.Scale(
                        domain=[
                            "Alta",
                            "Revisao Alto Valor",
                        ],
                        range=[
                            "#1E874B",
                            "#C9851A",
                        ],
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "categoria_relevante:N",
                        title="Categoria",
                    ),
                    alt.Tooltip(
                        "confidence_tier:N",
                        title="Confiança",
                    ),
                    alt.Tooltip(
                        "valor_formatado:N",
                        title="Potential Savings",
                    ),
                ],
            )
            .properties(
                height=280
            )
        )

        st.altair_chart(
            chart_savings,
            use_container_width=True,
        )

    # ========================================================
    # TOP OPPORTUNITIES
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Top High Confidence Opportunities'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Itens priorizados para investigação e negociação.'
        '</div>',
        unsafe_allow_html=True,
    )

    top_opportunities = (
        savings_alta
        .sort_values(
            "potential_saving",
            ascending=False,
        )
        .head(5)
        [
            [
                "nome_fornecedor",
                "categoria_relevante",
                "unit_price",
                "preco_esperado",
                "potential_saving",
                "priority",
            ]
        ]
        .rename(
            columns={
                "nome_fornecedor":
                    "Fornecedor",

                "categoria_relevante":
                    "Categoria",

                "unit_price":
                    "Preço observado",

                "preco_esperado":
                    "Preço esperado",

                "potential_saving":
                    "Impacto potencial",

                "priority":
                    "Prioridade",
            }
        )
    )

    st.dataframe(
        top_opportunities,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Preço observado":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),

            "Preço esperado":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),

            "Impacto potencial":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),
        },
    )

    st.caption(
        "Potential Savings é um indicador de priorização "
        "para revisão e negociação; não representa economia "
        "garantida, fraude ou sobrepreço comprovado."
    )


# ============================================================
# SPEND & SUPPLIERS
# ============================================================

if pagina == "Spend & Suppliers":

    fact_relevante = dados["fact"][
        dados["fact"]["categoria_relevante"]
        .notna()
    ].copy()

    dim_supplier = (
        dados["dim_supplier"][
            [
                "supplier_key",
                "nome_fornecedor",
            ]
        ]
        .drop_duplicates(
            "supplier_key"
        )
        .copy()
    )

    # --------------------------------------------------------
    # Analises globais
    # --------------------------------------------------------

    spend_cat = compute_spend_by_category(
        fact_relevante
    )

    hhi_cat = compute_hhi_by_category(
        fact_relevante
    )

    abc_global = build_supplier_abc_curve(
        fact_relevante
    )

    spend_total = float(
        spend_cat["spend_total"].sum()
    )

    n_categorias = int(
        spend_cat[
            "categoria_relevante"
        ].nunique()
    )

    n_fornecedores = int(
        abc_global["supplier_key"]
        .nunique()
    )

    top_categoria = (
        spend_cat.iloc[0]
    )

    n_categoria_alta_concentracao = int(
        (
            hhi_cat["classificacao_hhi"]
            == "altamente concentrado"
        ).sum()
    )

    # ========================================================
    # KPIs GLOBAIS
    # ========================================================

    cols = st.columns(5)

    cols[0].metric(
        "Spend Monitorado",
        formatar_brl_compacto(
            spend_total
        ),
    )

    cols[1].metric(
        "Categorias",
        f"{n_categorias}",
    )

    cols[2].metric(
        "Fornecedores",
        f"{n_fornecedores:,}"
        .replace(",", "."),
    )

    cols[3].metric(
        "Maior Categoria",
        top_categoria[
            "categoria_relevante"
        ],
    )

    cols[4].metric(
        "Categorias Altamente Concentradas",
        f"{n_categoria_alta_concentracao}",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================================
    # VISÃO GLOBAL
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Visão global'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Distribuição do gasto e concentração '
        'de fornecedores por categoria.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_spend, col_hhi = st.columns(2)

    # --------------------------------------------------------
    # Spend por categoria
    # --------------------------------------------------------

    with col_spend:

        chart_spend_df = (
            spend_cat
            .sort_values(
                "spend_total",
                ascending=False,
            )
            .copy()
        )

        chart_spend_df[
            "spend_formatado"
        ] = (
            chart_spend_df[
                "spend_total"
            ]
            .apply(
                formatar_brl_compacto
            )
        )

        chart_spend_df[
            "share_formatado"
        ] = (
            100
            * chart_spend_df[
                "spend_total"
            ]
            / spend_total
        ).map(
            lambda x:
                f"{x:.1f}%"
                .replace(".", ",")
        )

        chart_spend = (
            alt.Chart(
                chart_spend_df
            )
            .mark_bar(
                color="#5B0011",
                cornerRadiusEnd=4,
            )
            .encode(
                x=alt.X(
                    "spend_total:Q",
                    title=None,
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                        labels=False,
                        ticks=False,
                        domain=False,
                    ),
                ),

                y=alt.Y(
                    "categoria_relevante:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelColor="#7A7D85",
                        labelLimit=190,
                        domain=False,
                        ticks=False,
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "categoria_relevante:N",
                        title="Categoria",
                    ),

                    alt.Tooltip(
                        "spend_formatado:N",
                        title="Spend",
                    ),

                    alt.Tooltip(
                        "share_formatado:N",
                        title="Participação",
                    ),

                    alt.Tooltip(
                        "n_fornecedores_distintos:Q",
                        title="Fornecedores",
                    ),
                ],
            )
            .properties(
                title="Spend por categoria",
                height=300,
            )
        )

        st.altair_chart(
            chart_spend,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # HHI
    # --------------------------------------------------------

    with col_hhi:

        hhi_plot = hhi_cat.copy()

        mapa_hhi = {
            "nao concentrado":
                "Não concentrado",

            "moderadamente concentrado":
                "Moderado",

            "altamente concentrado":
                "Altamente concentrado",
        }

        hhi_plot["status_hhi"] = (
            hhi_plot[
                "classificacao_hhi"
            ]
            .map(mapa_hhi)
            .fillna(
                hhi_plot[
                    "classificacao_hhi"
                ]
            )
        )

        chart_hhi = (
            alt.Chart(
                hhi_plot
            )
            .mark_bar(
                cornerRadiusEnd=4
            )
            .encode(
                x=alt.X(
                    "hhi:Q",
                    title="HHI",
                    scale=alt.Scale(
                        domain=[
                            0,
                            max(
                                3000,
                                float(
                                    hhi_plot[
                                        "hhi"
                                    ].max()
                                )
                                * 1.05,
                            ),
                        ]
                    ),
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                        domain=False,
                    ),
                ),

                y=alt.Y(
                    "categoria_relevante:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelColor="#7A7D85",
                        labelLimit=190,
                        domain=False,
                        ticks=False,
                    ),
                ),

                color=alt.Color(
                    "status_hhi:N",
                    title="Concentração",
                    scale=alt.Scale(
                        domain=[
                            "Não concentrado",
                            "Moderado",
                            "Altamente concentrado",
                        ],
                        range=[
                            "#1E874B",
                            "#C9851A",
                            "#CC092F",
                        ],
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "categoria_relevante:N",
                        title="Categoria",
                    ),

                    alt.Tooltip(
                        "hhi:Q",
                        title="HHI",
                        format=".0f",
                    ),

                    alt.Tooltip(
                        "status_hhi:N",
                        title="Status",
                    ),

                    alt.Tooltip(
                        "top1_supplier_share_pct:Q",
                        title="Top 1",
                        format=".1f",
                    ),

                    alt.Tooltip(
                        "top3_supplier_share_pct:Q",
                        title="Top 3",
                        format=".1f",
                    ),
                ],
            )
            .properties(
                title="Concentração por categoria",
                height=300,
            )
        )

        st.altair_chart(
            chart_hhi,
            use_container_width=True,
        )

        st.caption(
            "HHI: <1.500 não concentrado · "
            "1.500–2.500 moderado · "
            ">2.500 altamente concentrado."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================================
    # DRILL-DOWN
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Análise de fornecedores por categoria'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Selecione uma categoria para investigar '
        'dependência, concentração e fornecedores críticos.'
        '</div>',
        unsafe_allow_html=True,
    )

    categorias = (
        spend_cat[
            "categoria_relevante"
        ]
        .tolist()
    )

    categoria_selecionada = (
        st.selectbox(
            "Categoria",
            categorias,
            index=0,
        )
    )

    # --------------------------------------------------------
    # Dados da categoria
    # --------------------------------------------------------

    categoria_row = (
        spend_cat[
            spend_cat[
                "categoria_relevante"
            ]
            == categoria_selecionada
        ]
        .iloc[0]
    )

    hhi_row = (
        hhi_cat[
            hhi_cat[
                "categoria_relevante"
            ]
            == categoria_selecionada
        ]
        .iloc[0]
    )

    abc = build_supplier_abc_curve(
        fact_relevante,
        category=categoria_selecionada,
    ).copy()

    # Tipagem segura para o join
    abc["supplier_key"] = (
        abc["supplier_key"]
        .astype("string")
    )

    dim_supplier_join = (
        dim_supplier.copy()
    )

    dim_supplier_join[
        "supplier_key"
    ] = (
        dim_supplier_join[
            "supplier_key"
        ]
        .astype("string")
    )

    abc = abc.merge(
        dim_supplier_join,
        on="supplier_key",
        how="left",
        validate="many_to_one",
    )

    abc["Fornecedor"] = (
        abc["nome_fornecedor"]
        .fillna(
            abc["supplier_key"]
        )
    )

    abc["rank"] = (
        range(
            1,
            len(abc) + 1,
        )
    )

    # --------------------------------------------------------
    # KPIs da categoria
    # --------------------------------------------------------

    status_hhi = mapa_hhi.get(
        hhi_row[
            "classificacao_hhi"
        ],
        hhi_row[
            "classificacao_hhi"
        ],
    )

    n_fornecedores_a = int(
        (
            abc["classe_abc"]
            == "A"
        ).sum()
    )

    top1_share = float(
        hhi_row[
            "top1_supplier_share_pct"
        ]
    )

    cat_cols = st.columns(5)

    cat_cols[0].metric(
        "Spend da Categoria",
        formatar_brl_compacto(
            categoria_row[
                "spend_total"
            ]
        ),
    )

    n_fornecedores_categoria = int(
    hhi_row["n_fornecedores_distintos"]
    )

    cat_cols[1].metric(
        "Fornecedores",
        f"{n_fornecedores_categoria:,}".replace(",", "."),
    )

    cat_cols[2].metric(
        "HHI",
        f"{hhi_row['hhi']:,.0f}"
        .replace(",", "."),
    )

    cat_cols[3].metric(
        "Participação do Maior Fornecedor",
        (
            f"{top1_share:.1f}%"
            .replace(".", ",")
        ),
    )

    cat_cols[4].metric(
        "Fornecedores Classe A",
        f"{n_fornecedores_a}",
    )

    st.caption(
        f"Status de concentração: {status_hhi}"
    )

    # ========================================================
    # TOP SUPPLIERS + ABC
    # ========================================================

    col_supplier, col_abc = (
        st.columns(2)
    )

    # --------------------------------------------------------
    # Ranking
    # --------------------------------------------------------

    with col_supplier:

        top_suppliers = (
            abc.head(15)
            .copy()
        )

        top_suppliers[
            "spend_formatado"
        ] = (
            top_suppliers[
                "total_price"
            ]
            .apply(
                formatar_brl_compacto
            )
        )

        supplier_chart = (
            alt.Chart(
                top_suppliers
            )
            .mark_bar(
                color="#5B0011",
                cornerRadiusEnd=4,
            )
            .encode(
                x=alt.X(
                    "total_price:Q",
                    title=None,
                    axis=alt.Axis(
                        labels=False,
                        ticks=False,
                        domain=False,
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                y=alt.Y(
                    "Fornecedor:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelColor="#7A7D85",
                        labelLimit=240,
                        domain=False,
                        ticks=False,
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "Fornecedor:N",
                        title="Fornecedor",
                    ),

                    alt.Tooltip(
                        "spend_formatado:N",
                        title="Spend",
                    ),

                    alt.Tooltip(
                        "share_pct:Q",
                        title="Share",
                        format=".1f",
                    ),

                    alt.Tooltip(
                        "classe_abc:N",
                        title="Classe ABC",
                    ),
                ],
            )
            .properties(
                title="Top fornecedores por spend",
                height=360,
            )
        )

        st.altair_chart(
            supplier_chart,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Curva ABC
    # --------------------------------------------------------

    with col_abc:

        abc_curve = (
            alt.Chart(
                abc
            )
            .mark_line(
                color="#CC092F",
                strokeWidth=2.5,
                point=False,
            )
            .encode(
                x=alt.X(
                    "rank:Q",
                    title="Ranking de fornecedores",
                    axis=alt.Axis(
                        grid=False,
                    ),
                ),

                y=alt.Y(
                    "cum_share_pct:Q",
                    title="Spend acumulado (%)",
                    scale=alt.Scale(
                        domain=[0, 100]
                    ),
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "rank:Q",
                        title="Posição",
                    ),

                    alt.Tooltip(
                        "Fornecedor:N",
                        title="Fornecedor",
                    ),

                    alt.Tooltip(
                        "cum_share_pct:Q",
                        title="Acumulado",
                        format=".1f",
                    ),

                    alt.Tooltip(
                        "classe_abc:N",
                        title="Classe",
                    ),
                ],
            )
        )

        linhas_referencia = (
            alt.Chart(
                {
                    "values": [
                        {
                            "y": 80,
                        },
                        {
                            "y": 95,
                        },
                    ]
                }
            )
            .mark_rule(
                color="#9AA0A6",
                strokeDash=[
                    6,
                    5,
                ],
            )
            .encode(
                y="y:Q"
            )
        )

        chart_abc = (
            abc_curve
            + linhas_referencia
        ).properties(
            title="Curva ABC de fornecedores",
            height=360,
        )

        st.altair_chart(
            chart_abc,
            use_container_width=True,
        )

        st.caption(
            "Classe A: até 80% do spend acumulado · "
            "Classe B: até 95% · Classe C: restante."
        )

    # ========================================================
    # TABELA EXECUTIVA
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Detalhamento de fornecedores'
        '</div>',
        unsafe_allow_html=True,
    )

    tabela_fornecedores = (
        abc[
            [
                "Fornecedor",
                "total_price",
                "share_pct",
                "cum_share_pct",
                "classe_abc",
            ]
        ]
        .head(30)
        .rename(
            columns={
                "total_price":
                    "Spend",

                "share_pct":
                    "Share (%)",

                "cum_share_pct":
                    "Share acumulado (%)",

                "classe_abc":
                    "Classe ABC",
            }
        )
    )

    st.dataframe(
        tabela_fornecedores,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Spend":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),

            "Share (%)":
                st.column_config.NumberColumn(
                    format="%.2f%%"
                ),

            "Share acumulado (%)":
                st.column_config.NumberColumn(
                    format="%.2f%%"
                ),
        },
    )


# ============================================================
# PRICE INTELLIGENCE
# ============================================================

if pagina == "Price Intelligence":

    errors = dados["oot_errors"].copy()
    anomalies = dados["anomalies_2026"].copy()

    # --------------------------------------------------------
    # Segmentacao Known / Unseen
    # --------------------------------------------------------

    errors["segmento_item"] = (
        errors["is_known_item"]
        .fillna(False)
        .astype(bool)
        .map(
            {
                True: "Known",
                False: "Unseen",
            }
        )
    )

    known_mask = (
        errors["is_known_item"]
        .fillna(False)
        .astype(bool)
    )

    n_total = len(errors)

    n_known = int(
        known_mask.sum()
    )

    n_unseen = (
        n_total - n_known
    )

    mae_log = float(
        errors["abs_log_error"].mean()
    )

    known_mae = float(
        errors.loc[
            known_mask,
            "abs_log_error",
        ].mean()
    )

    unseen_rate = (
        100 * n_unseen / n_total
        if n_total
        else 0.0
    )

    # --------------------------------------------------------
    # Anomalias
    # --------------------------------------------------------

    known_anomalies_mask = (
        anomalies["is_known_item"]
        .fillna(False)
        .astype(bool)
    )

    n_known_anomalies_base = int(
        known_anomalies_mask.sum()
    )

    n_anomalias = int(
        anomalies[
            "is_price_anomaly"
        ]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    anomaly_rate = (
        100
        * n_anomalias
        / n_known_anomalies_base
        if n_known_anomalies_base
        else 0.0
    )

    n_acima = int(
        (
            anomalies[
                "anomaly_direction"
            ]
            == "acima_do_esperado"
        ).sum()
    )

    threshold = None

    if (
        "anomaly_threshold_abs_log"
        in anomalies.columns
    ):
        threshold_values = (
            anomalies[
                "anomaly_threshold_abs_log"
            ]
            .dropna()
        )

        if not threshold_values.empty:
            threshold = float(
                threshold_values.iloc[0]
            )

    # ========================================================
    # KPIs
    # ========================================================

    cols = st.columns(5)

    cols[0].metric(
        "Transações OOT 2026",
        f"{n_total:,}".replace(",", "."),
    )

    cols[1].metric(
        "MAE log",
        f"{mae_log:.4f}".replace(".", ","),
    )

    cols[2].metric(
        "Known MAE",
        f"{known_mae:.4f}".replace(".", ","),
    )

    cols[3].metric(
        "Unseen Rate",
        f"{unseen_rate:.2f}%".replace(".", ","),
    )

    cols[4].metric(
        "Anomaly Rate · Known",
        f"{anomaly_rate:.2f}%".replace(".", ","),
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================================
    # LEITURA
    # ========================================================

    threshold_text = (
        f"{threshold:.3f}".replace(".", ",")
        if threshold is not None
        else "threshold calibrado"
    )

    mae_log_fmt = formatar_decimal(
        mae_log,
        4,
    )

    known_mae_fmt = formatar_decimal(
        known_mae,
        4,
    )

    unseen_rate_fmt = formatar_percentual(
        unseen_rate,
        1,
    )

    anomaly_rate_fmt = formatar_percentual(
        anomaly_rate,
        2,
    )

    threshold_fmt = (
        formatar_decimal(
            threshold,
            3,
        )
        if threshold is not None
        else "calibrado"
    )

    price_reading_html = (
        '<div class="pi-insight">'
        '<div class="pi-insight-title">'
        'Leitura de Price Intelligence'
        '</div>'

        f'<p>O modelo avaliou '
        f'<strong>{formatar_inteiro(n_total)}</strong> '
        f'transações no período OOT de 2026.</p>'

        f'<p>Entre os itens conhecidos, o MAE log foi '
        f'<strong>{known_mae_fmt}</strong>. '
        f'Itens unseen representam '
        f'<strong>{unseen_rate_fmt}</strong> '
        f'da população e são tratados separadamente '
        f'na camada de monitoramento.</p>'

        f'<p>O threshold congelado de anomalia é '
        f'<strong>|log error| ≥ {threshold_fmt}</strong>. '
        f'Foram identificadas '
        f'<strong>{formatar_inteiro(n_anomalias)}</strong> '
        f'anomalias entre itens conhecidos, sendo '
        f'<strong>{formatar_inteiro(n_acima)}</strong> '
        f'acima do preço esperado.</p>'

        '</div>'
    )

    st.markdown(
        price_reading_html,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ========================================================
    # DIAGNOSTICO VISUAL
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Diagnóstico do modelo'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Relação entre preços observados, preços esperados '
        'e distribuição dos erros OOT.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_scatter, col_error = st.columns(2)

    # --------------------------------------------------------
    # Observado vs esperado
    # --------------------------------------------------------

    with col_scatter:

        scatter_df = (
            errors[
                [
                    "unit_price",
                    "unit_price_pred",
                    "abs_log_error",
                    "segmento_item",
                ]
            ]
            .dropna()
            .copy()
        )

        if len(scatter_df) > 5000:
            scatter_df = (
                scatter_df
                .sample(
                    n=5000,
                    random_state=42,
                )
            )

        min_price = float(
            min(
                scatter_df[
                    "unit_price"
                ].min(),
                scatter_df[
                    "unit_price_pred"
                ].min(),
            )
        )

        max_price = float(
            max(
                scatter_df[
                    "unit_price"
                ].max(),
                scatter_df[
                    "unit_price_pred"
                ].max(),
            )
        )

        min_price = max(
            min_price,
            0.01,
        )

        if max_price <= min_price:
            max_price = (
                min_price * 10
            )

        scatter = (
            alt.Chart(
                scatter_df
            )
            .mark_circle(
                size=28,
                opacity=0.38,
            )
            .encode(
                x=alt.X(
                    "unit_price_pred:Q",
                    title="Preço esperado",
                    scale=alt.Scale(
                        type="log",
                        domain=[
                            min_price,
                            max_price,
                        ],
                    ),
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                y=alt.Y(
                    "unit_price:Q",
                    title="Preço observado",
                    scale=alt.Scale(
                        type="log",
                        domain=[
                            min_price,
                            max_price,
                        ],
                    ),
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                color=alt.Color(
                    "segmento_item:N",
                    title="Item",
                    scale=alt.Scale(
                        domain=[
                            "Known",
                            "Unseen",
                        ],
                        range=[
                            "#5B0011",
                            "#2B6CB0",
                        ],
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "segmento_item:N",
                        title="Item",
                    ),
                    alt.Tooltip(
                        "unit_price:Q",
                        title="Preço observado",
                        format=",.2f",
                    ),
                    alt.Tooltip(
                        "unit_price_pred:Q",
                        title="Preço esperado",
                        format=",.2f",
                    ),
                    alt.Tooltip(
                        "abs_log_error:Q",
                        title="Erro log",
                        format=".3f",
                    ),
                ],
            )
        )

        referencia = (
            alt.Chart(
                {
                    "values": [
                        {
                            "esperado": min_price,
                            "observado": min_price,
                        },
                        {
                            "esperado": max_price,
                            "observado": max_price,
                        },
                    ]
                }
            )
            .mark_line(
                color="#9AA0A6",
                strokeDash=[
                    6,
                    5,
                ],
                strokeWidth=1.5,
            )
            .encode(
                x="esperado:Q",
                y="observado:Q",
            )
        )

        chart_scatter = (
            scatter
            + referencia
        ).properties(
            title=(
                "Preço observado vs esperado"
            ),
            height=330,
        )

        st.altair_chart(
            chart_scatter,
            use_container_width=True,
        )

        st.caption(
            "Escala logarítmica. A linha tracejada "
            "representa preço observado = preço esperado."
        )

    # --------------------------------------------------------
    # Distribuicao dos erros
    # --------------------------------------------------------

    with col_error:

        histogram = (
            alt.Chart(
                errors
            )
            .mark_bar(
                opacity=0.82
            )
            .encode(
                x=alt.X(
                    "abs_log_error:Q",
                    bin=alt.Bin(
                        maxbins=45
                    ),
                    title="Erro absoluto em log",
                    axis=alt.Axis(
                        grid=False,
                    ),
                ),

                y=alt.Y(
                    "count():Q",
                    title="Observações",
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                color=alt.Color(
                    "segmento_item:N",
                    title="Item",
                    scale=alt.Scale(
                        domain=[
                            "Known",
                            "Unseen",
                        ],
                        range=[
                            "#5B0011",
                            "#2B6CB0",
                        ],
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "count():Q",
                        title="Observações",
                    ),
                ],
            )
        )

        if threshold is not None:

            threshold_rule = (
                alt.Chart(
                    {
                        "values": [
                            {
                                "threshold":
                                    threshold
                            }
                        ]
                    }
                )
                .mark_rule(
                    color="#CC092F",
                    strokeDash=[
                        6,
                        5,
                    ],
                    strokeWidth=2,
                )
                .encode(
                    x="threshold:Q"
                )
            )

            histogram = (
                histogram
                + threshold_rule
            )

        histogram = (
            histogram
            .properties(
                title="Distribuição dos erros OOT",
                height=330,
            )
        )

        st.altair_chart(
            histogram,
            use_container_width=True,
        )

        if threshold is not None:
            st.caption(
                "Linha vermelha tracejada: "
                "threshold de anomalia congelado "
                "na validação de 2025."
            )

    # ========================================================
    # ANOMALIAS
    # ========================================================

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="pi-section-title">'
        'Price Anomalies'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Casos conhecidos que ultrapassaram o threshold '
        'estatístico calibrado em 2025.'
        '</div>',
        unsafe_allow_html=True,
    )

    anomaly_rows = (
        anomalies[
            anomalies[
                "is_price_anomaly"
            ]
            .fillna(False)
            .astype(bool)
        ]
        .copy()
    )

    anomaly_direction_map = {
        "acima_do_esperado":
            "Acima do esperado",

        "abaixo_do_esperado":
            "Abaixo do esperado",
    }

    anomaly_rows[
        "Direção"
    ] = (
        anomaly_rows[
            "anomaly_direction"
        ]
        .map(
            anomaly_direction_map
        )
        .fillna(
            anomaly_rows[
                "anomaly_direction"
            ]
        )
    )

    kpi_anomaly_cols = (
        st.columns(3)
    )

    kpi_anomaly_cols[0].metric(
        "Anomalias Known",
        f"{len(anomaly_rows):,}"
        .replace(",", "."),
    )

    kpi_anomaly_cols[1].metric(
        "Acima do Esperado",
        f"{n_acima:,}"
        .replace(",", "."),
    )

    n_abaixo = int(
        (
            anomaly_rows[
                "anomaly_direction"
            ]
            == "abaixo_do_esperado"
        ).sum()
    )

    kpi_anomaly_cols[2].metric(
        "Abaixo do Esperado",
        f"{n_abaixo:,}"
        .replace(",", "."),
    )

    # --------------------------------------------------------
    # Filtro
    # --------------------------------------------------------

    filtro_direcao = st.selectbox(
        "Direção da anomalia",
        [
            "Todas",
            "Acima do esperado",
            "Abaixo do esperado",
        ],
    )

    anomaly_filtered = (
        anomaly_rows.copy()
    )

    if filtro_direcao != "Todas":
        anomaly_filtered = (
            anomaly_filtered[
                anomaly_filtered[
                    "Direção"
                ]
                == filtro_direcao
            ]
        )

    # --------------------------------------------------------
    # Ranking
    # --------------------------------------------------------

    anomaly_filtered = (
        anomaly_filtered
        .sort_values(
            "abs_log_error",
            ascending=False,
        )
    )

    colunas_anomalias = [
        coluna
        for coluna in [
            "item_key",
            "unit_price",
            "unit_price_pred",
            "price_deviation_pct",
            "abs_log_error",
            "Direção",
        ]
        if coluna
        in anomaly_filtered.columns
    ]

    tabela_anomalias = (
        anomaly_filtered[
            colunas_anomalias
        ]
        .head(50)
        .rename(
            columns={
                "item_key":
                    "Item",

                "unit_price":
                    "Preço observado",

                "unit_price_pred":
                    "Preço esperado",

                "price_deviation_pct":
                    "Desvio (%)",

                "abs_log_error":
                    "Erro log",
            }
        )
    )

    st.dataframe(
        tabela_anomalias,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Preço observado":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),

            "Preço esperado":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),

            "Desvio (%)":
                st.column_config.NumberColumn(
                    format="%.2f%%"
                ),

            "Erro log":
                st.column_config.NumberColumn(
                    format="%.3f"
                ),
        },
    )

    st.caption(
        "Anomalia estatística não representa fraude "
        "ou sobrepreço comprovado. Casos acima do esperado "
        "seguem para a camada de Savings, onde passam por "
        "regras adicionais de qualidade e confiança."
    )

# ============================================================
# SAVINGS OPPORTUNITIES
# ============================================================

if pagina == "Savings Opportunities":

    savings = dados["savings"].copy()

    # --------------------------------------------------------
    # Segmentos oficiais
    # --------------------------------------------------------

    alta = savings[
        savings["confidence_tier"]
        == "Alta"
    ].copy()

    revisao = savings[
        savings["confidence_tier"]
        == "Revisao Alto Valor"
    ].copy()

    baixa = savings[
        savings["confidence_tier"]
        == "Baixa"
    ].copy()

    savings_alta = float(
        alta["potential_saving"].sum()
    )

    savings_revisao = float(
        revisao["potential_saving"].sum()
    )

    n_alta = len(alta)
    n_revisao = len(revisao)
    n_baixa = len(baixa)

    # ========================================================
    # KPIs
    # ========================================================

    cols = st.columns(5)

    cols[0].metric(
        "Potential Savings — Alta Confiança",
        formatar_brl_compacto(
            savings_alta
        ),
    )

    cols[1].metric(
        "Oportunidades de Alta Confiança",
        formatar_inteiro(
            n_alta
        ),
    )

    cols[2].metric(
        "Alto Valor em Revisão",
        formatar_brl_compacto(
            savings_revisao
        ),
    )

    cols[3].metric(
        "Itens em Revisão",
        formatar_inteiro(
            n_revisao
        ),
    )

    cols[4].metric(
        "Baixa Confiança",
        formatar_inteiro(
            n_baixa
        ),
    )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # LEITURA EXECUTIVA
    # ========================================================

    if not alta.empty:

        savings_cat_alta = (
            alta
            .groupby(
                "categoria_relevante",
                dropna=False,
            )["potential_saving"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        top_categoria = (
            savings_cat_alta.index[0]
        )

        top_categoria_valor = float(
            savings_cat_alta.iloc[0]
        )

        savings_supplier_alta = (
            alta
            .groupby(
                "nome_fornecedor",
                dropna=False,
            )["potential_saving"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        top_supplier = (
            savings_supplier_alta.index[0]
        )

        top_supplier_valor = float(
            savings_supplier_alta.iloc[0]
        )

    else:

        top_categoria = (
            "Sem oportunidades"
        )

        top_categoria_valor = 0.0

        top_supplier = (
            "Sem oportunidades"
        )

        top_supplier_valor = 0.0

    st.markdown(
        dedent(
            f"""
            <div class="pi-insight">
                <div class="pi-insight-title">
                    Leitura executiva
                </div>
                <p>
                    Foram identificados
                    <strong>
                        {formatar_brl_compacto(savings_alta)}
                    </strong>
                    em
                    <strong>{n_alta}</strong>
                    oportunidades classificadas como
                    High Confidence.
                </p>
                <p>
                    A categoria com maior impacto potencial
                    é
                    <strong>{top_categoria}</strong>,
                    com
                    <strong>
                        {formatar_brl_compacto(
                            top_categoria_valor
                        )}
                    </strong>.
                </p>
                <p>
                    O fornecedor com maior oportunidade
                    agregada de alta confiança é
                    <strong>{top_supplier}</strong>,
                    com
                    <strong>
                        {formatar_brl_compacto(
                            top_supplier_valor
                        )}
                    </strong>.
                </p>
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    st.markdown(
        dedent(
            f"""
            <div class="pi-monitoring-note">
                <strong>Validação manual necessária:</strong>
                existem
                <strong>
                    {formatar_brl_compacto(savings_revisao)}
                </strong>
                distribuídos em
                <strong>{n_revisao}</strong>
                oportunidades de alto valor que passaram
                pelas regras de qualidade, mas permanecem
                fora do KPI principal por exigirem revisão
                adicional.
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # VISÃO FINANCEIRA
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Distribuição das oportunidades'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Impacto financeiro por categoria, confiança '
        'e prioridade de atuação.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_categoria, col_prioridade = (
        st.columns(2)
    )

    # --------------------------------------------------------
    # Savings por categoria
    # --------------------------------------------------------

    with col_categoria:

        chart_confidence_df = (
            savings[
                savings[
                    "confidence_tier"
                ].isin(
                    [
                        "Alta",
                        "Revisao Alto Valor",
                    ]
                )
            ]
            .groupby(
                [
                    "categoria_relevante",
                    "confidence_tier",
                ],
                dropna=False,
            )[
                "potential_saving"
            ]
            .sum()
            .reset_index()
        )

        confidence_label_map = {
            "Alta":
                "High Confidence",

            "Revisao Alto Valor":
                "High-Value Review",
        }

        chart_confidence_df[
            "confidence_label"
        ] = (
            chart_confidence_df[
                "confidence_tier"
            ]
            .map(
                confidence_label_map
            )
        )

        chart_confidence_df[
            "valor_formatado"
        ] = (
            chart_confidence_df[
                "potential_saving"
            ]
            .apply(
                formatar_brl_compacto
            )
        )

        chart_categoria = (
            alt.Chart(
                chart_confidence_df
            )
            .mark_bar(
                cornerRadiusEnd=3
            )
            .encode(
                x=alt.X(
                    "potential_saving:Q",
                    title=None,
                    axis=alt.Axis(
                        labels=False,
                        ticks=False,
                        domain=False,
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                y=alt.Y(
                    "categoria_relevante:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(
                        labelColor="#7A7D85",
                        labelLimit=190,
                        domain=False,
                        ticks=False,
                    ),
                ),

                color=alt.Color(
                    "confidence_label:N",
                    title="Confiança",
                    scale=alt.Scale(
                        domain=[
                            "High Confidence",
                            "High-Value Review",
                        ],
                        range=[
                            "#1E874B",
                            "#C9851A",
                        ],
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "categoria_relevante:N",
                        title="Categoria",
                    ),

                    alt.Tooltip(
                        "confidence_label:N",
                        title="Confiança",
                    ),

                    alt.Tooltip(
                        "valor_formatado:N",
                        title="Potential Savings",
                    ),
                ],
            )
            .properties(
                title=(
                    "Potential Savings por categoria"
                ),
                height=320,
            )
        )

        st.altair_chart(
            chart_categoria,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Savings por prioridade
    # --------------------------------------------------------

    with col_prioridade:

        prioridade_df = (
            savings[
                savings[
                    "confidence_tier"
                ].isin(
                    [
                        "Alta",
                        "Revisao Alto Valor",
                    ]
                )
            ]
            .groupby(
                "priority",
                dropna=False,
            )
            .agg(
                potential_saving=(
                    "potential_saving",
                    "sum",
                ),
                oportunidades=(
                    "potential_saving",
                    "size",
                ),
            )
            .reset_index()
        )

        prioridade_label_map = {
            "Alta":
                "Alta",

            "Media":
                "Média",

            "Baixa":
                "Baixa",
        }

        prioridade_df[
            "prioridade_label"
        ] = (
            prioridade_df[
                "priority"
            ]
            .map(
                prioridade_label_map
            )
            .fillna(
                prioridade_df[
                    "priority"
                ]
            )
        )

        prioridade_df[
            "valor_formatado"
        ] = (
            prioridade_df[
                "potential_saving"
            ]
            .apply(
                formatar_brl_compacto
            )
        )

        chart_prioridade = (
            alt.Chart(
                prioridade_df
            )
            .mark_bar(
                cornerRadiusEnd=4
            )
            .encode(
                x=alt.X(
                    "potential_saving:Q",
                    title=None,
                    axis=alt.Axis(
                        labels=False,
                        ticks=False,
                        domain=False,
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                y=alt.Y(
                    "prioridade_label:N",
                    title=None,
                    sort=[
                        "Alta",
                        "Média",
                        "Baixa",
                    ],
                    axis=alt.Axis(
                        labelColor="#7A7D85",
                        domain=False,
                        ticks=False,
                    ),
                ),

                color=alt.Color(
                    "prioridade_label:N",
                    title="Prioridade",
                    scale=alt.Scale(
                        domain=[
                            "Alta",
                            "Média",
                            "Baixa",
                        ],
                        range=[
                            "#CC092F",
                            "#C9851A",
                            "#9AA0A6",
                        ],
                    ),
                    legend=None,
                ),

                tooltip=[
                    alt.Tooltip(
                        "prioridade_label:N",
                        title="Prioridade",
                    ),

                    alt.Tooltip(
                        "valor_formatado:N",
                        title="Potential Savings",
                    ),

                    alt.Tooltip(
                        "oportunidades:Q",
                        title="Oportunidades",
                    ),
                ],
            )
            .properties(
                title=(
                    "Impacto por prioridade"
                ),
                height=320,
            )
        )

        st.altair_chart(
            chart_prioridade,
            use_container_width=True,
        )

    # ========================================================
    # FILTROS / FILA DE DECISÃO
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-title">'
        'Opportunity Review Queue'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Fila priorizada para investigação, negociação '
        'ou validação manual.'
        '</div>',
        unsafe_allow_html=True,
    )

    filtro_col1, filtro_col2, filtro_col3 = (
        st.columns(3)
    )

    with filtro_col1:

        confidence_options = [
            "Alta",
            "Revisao Alto Valor",
            "Baixa",
        ]

        confidence_selected = st.multiselect(
            "Confiança",
            confidence_options,
            default=[
                "Alta",
                "Revisao Alto Valor",
            ],
        )

    with filtro_col2:

        categorias_disponiveis = (
            savings[
                "categoria_relevante"
            ]
            .dropna()
            .sort_values()
            .unique()
            .tolist()
        )

        categoria_selected = st.multiselect(
            "Categoria",
            categorias_disponiveis,
        )

    with filtro_col3:

        priority_options = [
            valor
            for valor in [
                "Alta",
                "Media",
                "Baixa",
            ]
            if valor
            in savings[
                "priority"
            ].dropna().unique()
        ]

        priority_selected = st.multiselect(
            "Prioridade",
            priority_options,
        )

    filtered = savings.copy()

    if confidence_selected:

        filtered = filtered[
            filtered[
                "confidence_tier"
            ].isin(
                confidence_selected
            )
        ]

    else:

        filtered = filtered.iloc[0:0]

    if categoria_selected:

        filtered = filtered[
            filtered[
                "categoria_relevante"
            ].isin(
                categoria_selected
            )
        ]

    if priority_selected:

        filtered = filtered[
            filtered[
                "priority"
            ].isin(
                priority_selected
            )
        ]

    filtered = (
        filtered
        .sort_values(
            "potential_saving",
            ascending=False,
        )
    )

    # --------------------------------------------------------
    # Resumo do filtro
    # --------------------------------------------------------

    filtro_total = float(
        filtered[
            "potential_saving"
        ].sum()
    )

    resumo_cols = st.columns(3)

    resumo_cols[0].metric(
        "Oportunidades Selecionadas",
        f"{len(filtered):,}"
        .replace(",", "."),
    )

    resumo_cols[1].metric(
        "Impacto Potencial Selecionado",
        formatar_brl_compacto(
            filtro_total
        ),
    )

    if not filtered.empty:

        impacto_medio = float(
            filtered[
                "potential_saving"
            ].mean()
        )

    else:

        impacto_medio = 0.0

    resumo_cols[2].metric(
        "Impacto Médio",
        formatar_brl_compacto(
            impacto_medio
        ),
    )

    # ========================================================
    # TABELA
    # ========================================================

    confidence_display = {
        "Alta":
            "High Confidence",

        "Revisao Alto Valor":
            "High-Value Review",

        "Baixa":
            "Low Confidence",
    }

    priority_display = {
        "Alta":
            "Alta",

        "Media":
            "Média",

        "Baixa":
            "Baixa",
    }

    tabela = filtered.copy()

    tabela[
        "Confiança"
    ] = (
        tabela[
            "confidence_tier"
        ]
        .map(
            confidence_display
        )
    )

    tabela[
        "Prioridade"
    ] = (
        tabela[
            "priority"
        ]
        .map(
            priority_display
        )
        .fillna(
            tabela[
                "priority"
            ]
        )
    )

    colunas_tabela = [
        "Prioridade",
        "Confiança",
        "nome_fornecedor",
        "categoria_relevante",
        "descricao_resumida_amostra",
        "unit_price",
        "preco_esperado",
        "quantity",
        "price_deviation_pct",
        "potential_saving",
        "n_historico",
    ]

    tabela = (
        tabela[
            colunas_tabela
        ]
        .head(100)
        .rename(
            columns={
                "nome_fornecedor":
                    "Fornecedor",

                "categoria_relevante":
                    "Categoria",

                "descricao_resumida_amostra":
                    "Descrição",

                "unit_price":
                    "Preço observado",

                "preco_esperado":
                    "Preço esperado",

                "quantity":
                    "Quantidade",

                "price_deviation_pct":
                    "Desvio (%)",

                "potential_saving":
                    "Impacto potencial",

                "n_historico":
                    "Histórico",
            }
        )
    )

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Preço observado":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),

            "Preço esperado":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),

            "Quantidade":
                st.column_config.NumberColumn(
                    format="%.2f"
                ),

            "Desvio (%)":
                st.column_config.NumberColumn(
                    format="%.2f%%"
                ),

            "Impacto potencial":
                st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),

            "Histórico":
                st.column_config.NumberColumn(
                    format="%d"
                ),
        },
    )

    st.caption(
        "Potential Savings é um indicador de priorização "
        "para revisão e negociação. Não representa economia "
        "garantida, fraude ou sobrepreço comprovado."
    )

    # ========================================================
    # LOW CONFIDENCE — DIAGNOSTICO
    # ========================================================

    with st.expander(
        "Por que existem oportunidades de baixa confiança?"
    ):

        st.write(
            "Oportunidades classificadas como Low Confidence "
            "permanecem disponíveis para diagnóstico, mas "
            "não entram nos KPIs executivos."
        )

        low_flags = {
            "Unidade não comparável":
                int(
                    baixa[
                        "flag_unidade_nao_comparavel"
                    ].fillna(False).sum()
                ),

            "Pouco histórico":
                int(
                    baixa[
                        "flag_pouco_historico"
                    ].fillna(False).sum()
                ),

            "Inconsistência de total":
                int(
                    baixa[
                        "flag_inconsistencia_total"
                    ].fillna(False).sum()
                ),

            "Resultado conflitante":
                int(
                    baixa[
                        "flag_resultado_conflitante"
                    ].fillna(False).sum()
                ),
        }

        low_flags_df = (
            pd.DataFrame(
                {
                    "Motivo": list(
                        low_flags.keys()
                    ),
                    "Oportunidades": list(
                        low_flags.values()
                    ),
                }
            )
        )

        st.dataframe(
            low_flags_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# MODEL MONITORING
# ============================================================

if pagina == "Model Monitoring":

    overall = (
        dados["stability_overall"]
        .copy()
    )

    cold = (
        dados["stability_cold_start"]
        .copy()
    )

    category = (
        dados["stability_category"]
        .copy()
    )

    monthly = (
        dados["monthly_2026"]
        .copy()
    )

    mix = (
        dados["category_mix_drift"]
        .copy()
    )

    stability_summary = (
        dados["stability_summary"]
    )

    anomaly_summary = (
        dados["anomaly_summary"]
    )

    # ========================================================
    # METRICAS PRINCIPAIS
    # ========================================================

    mae_row = (
        overall[
            overall["metrica"]
            == "mae_log"
        ]
        .iloc[0]
    )

    mae_2025 = float(
        mae_row["valor_2025"]
    )

    mae_2026 = float(
        mae_row["valor_2026"]
    )

    mae_delta_pct = float(
        mae_row["delta_pct"]
    )

    known_2025 = (
        cold[
            (cold["ano"].astype(str) == "2025")
            & (cold["status"] == "known")
        ]
        .iloc[0]
    )

    known_2026 = (
        cold[
            (cold["ano"].astype(str) == "2026")
            & (cold["status"] == "known")
        ]
        .iloc[0]
    )

    unseen_2025 = (
        cold[
            (cold["ano"].astype(str) == "2025")
            & (cold["status"] == "unseen")
        ]
        .iloc[0]
    )

    unseen_2026 = (
        cold[
            (cold["ano"].astype(str) == "2026")
            & (cold["status"] == "unseen")
        ]
        .iloc[0]
    )

    known_mae_2025 = float(
        known_2025["mae_log"]
    )

    known_mae_2026 = float(
        known_2026["mae_log"]
    )

    unseen_mae_2025 = float(
        unseen_2025["mae_log"]
    )

    unseen_mae_2026 = float(
        unseen_2026["mae_log"]
    )

    unseen_rate_2025 = float(
        stability_summary[
            "unseen_item_rate_2025"
        ]
    )

    unseen_rate_2026 = float(
        stability_summary[
            "unseen_item_rate_2026"
        ]
    )

    unseen_delta_pp = (
        unseen_rate_2026
        - unseen_rate_2025
    )

    category_tvd = float(
        stability_summary[
            "category_mix_tvd_pct"
        ]
    )

    anomaly_rate_2025 = float(
        anomaly_summary[
            "validation_2025"
        ][
            "anomaly_rate_pct"
        ]
    )

    anomaly_rate_2026 = float(
        anomaly_summary[
            "oot_2026"
        ][
            "anomaly_rate_pct"
        ]
    )

    # ========================================================
    # KPIs
    # ========================================================

    cols = st.columns(6)

    cols[0].metric(
        "MAE log · 2025",
        f"{mae_2025:.4f}"
        .replace(".", ","),
    )

    cols[1].metric(
        "MAE log · OOT 2026",
        f"{mae_2026:.4f}"
        .replace(".", ","),
        delta=(
            f"{mae_delta_pct:+.2f}%"
            .replace(".", ",")
        ),
        delta_color="inverse",
    )

    cols[2].metric(
        "Known MAE · 2026",
        f"{known_mae_2026:.4f}"
        .replace(".", ","),
    )

    cols[3].metric(
        "Unseen Rate · 2026",
        (
            f"{unseen_rate_2026:.2f}%"
            .replace(".", ",")
        ),
        delta=(
            f"{unseen_delta_pp:+.2f} p.p."
            .replace(".", ",")
        ),
        delta_color="inverse",
    )

    cols[4].metric(
        "Anomaly Rate · 2026",
        (
            f"{anomaly_rate_2026:.2f}%"
            .replace(".", ",")
        ),
    )

    cols[5].metric(
        "Category Mix TVD",
        (
            f"{category_tvd:.2f}%"
            .replace(".", ",")
        ),
    )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # LEITURA EXECUTIVA
    # ========================================================

    known_delta_pct = (
        100
        * (
            known_mae_2026
            / known_mae_2025
            - 1
        )
    )

    unseen_delta_pct = (
        100
        * (
            unseen_mae_2026
            / unseen_mae_2025
            - 1
        )
    )

    anomaly_delta_pp = (
        anomaly_rate_2026
        - anomaly_rate_2025
    )

    mae_2025_fmt = (
        f"{mae_2025:.4f}".replace(".", ",")
    )

    mae_2026_fmt = (
        f"{mae_2026:.4f}".replace(".", ",")
    )

    mae_delta_fmt = (
        f"{mae_delta_pct:+.2f}".replace(".", ",")
    )

    known_mae_2025_fmt = (
        f"{known_mae_2025:.4f}".replace(".", ",")
    )

    known_mae_2026_fmt = (
        f"{known_mae_2026:.4f}".replace(".", ",")
    )

    known_delta_fmt = (
        f"{known_delta_pct:+.2f}".replace(".", ",")
    )

    unseen_rate_2025_fmt = (
        f"{unseen_rate_2025:.2f}".replace(".", ",")
    )

    unseen_rate_2026_fmt = (
        f"{unseen_rate_2026:.2f}".replace(".", ",")
    )

    unseen_delta_fmt = (
        f"{unseen_delta_pp:+.2f}".replace(".", ",")
    )

    anomaly_rate_2025_fmt = (
        f"{anomaly_rate_2025:.2f}".replace(".", ",")
    )

    anomaly_rate_2026_fmt = (
        f"{anomaly_rate_2026:.2f}".replace(".", ",")
    )

    anomaly_delta_fmt = (
        f"{anomaly_delta_pp:+.2f}".replace(".", ",")
    )

    leitura_estabilidade_html = (
        '<div class="pi-insight">'
        '<div class="pi-insight-title">Leitura de estabilidade</div>'

        f'<p>O MAE log global passou de '
        f'<strong>{mae_2025_fmt}</strong> para '
        f'<strong>{mae_2026_fmt}</strong>, '
        f'uma variação de '
        f'<strong>{mae_delta_fmt}%</strong>.</p>'

        f'<p>Entre itens conhecidos, o MAE permaneceu '
        f'praticamente estável: '
        f'<strong>{known_mae_2025_fmt}</strong> em 2025 versus '
        f'<strong>{known_mae_2026_fmt}</strong> em 2026 '
        f'(<strong>{known_delta_fmt}%</strong>).</p>'

        f'<p>O principal sinal de mudança está no mix: '
        f'itens unseen passaram de '
        f'<strong>{unseen_rate_2025_fmt}%</strong> para '
        f'<strong>{unseen_rate_2026_fmt}%</strong>, '
        f'aumento de '
        f'<strong>{unseen_delta_fmt} p.p.</strong>.</p>'

        f'<p>A taxa de anomalias conhecidas permaneceu '
        f'próxima da calibração: '
        f'<strong>{anomaly_rate_2025_fmt}%</strong> em 2025 versus '
        f'<strong>{anomaly_rate_2026_fmt}%</strong> em 2026 '
        f'(<strong>{anomaly_delta_fmt} p.p.</strong>).</p>'

        '</div>'
    )

    st.markdown(
        leitura_estabilidade_html,
        unsafe_allow_html=True,
    )

    st.markdown(
        dedent(
            """
            <div class="pi-monitoring-note">
                <strong>Nota metodológica:</strong>
                a validação de 2025 utiliza o LightGBM
                treinado em 2024, enquanto o teste OOT 2026
                utiliza o modelo final treinado em
                2024 + 2025. Portanto, a comparação abaixo
                representa estabilidade temporal operacional,
                não uma estimativa causal pura de model drift.
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # ESTABILIDADE MENSAL
    # ========================================================

    st.markdown(
        '<div class="pi-section-title">'
        'Estabilidade ao longo de 2026'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Performance mensal e evolução da incidência '
        'de itens unseen.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_mae_month, col_unseen_month = (
        st.columns(2)
    )

    # --------------------------------------------------------
    # MAE mensal
    # --------------------------------------------------------

    with col_mae_month:

        monthly_mae_chart = (
            alt.Chart(
                monthly
            )
            .mark_line(
                color="#5B0011",
                strokeWidth=2.5,
                point=alt.OverlayMarkDef(
                    filled=True,
                    size=55,
                ),
            )
            .encode(
                x=alt.X(
                    "mes:N",
                    title=None,
                    sort=None,
                    axis=alt.Axis(
                        labelAngle=0,
                        grid=False,
                    ),
                ),

                y=alt.Y(
                    "mae_log:Q",
                    title="MAE log",
                    scale=alt.Scale(
                        zero=False
                    ),
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "mes:N",
                        title="Mês",
                    ),

                    alt.Tooltip(
                        "n:Q",
                        title="Observações",
                    ),

                    alt.Tooltip(
                        "mae_log:Q",
                        title="MAE log",
                        format=".4f",
                    ),

                    alt.Tooltip(
                        "rmse_log:Q",
                        title="RMSE log",
                        format=".4f",
                    ),
                ],
            )
            .properties(
                title="MAE log mensal",
                height=290,
            )
        )

        st.altair_chart(
            monthly_mae_chart,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Unseen mensal
    # --------------------------------------------------------

    with col_unseen_month:

        monthly_unseen_chart = (
            alt.Chart(
                monthly
            )
            .mark_line(
                color="#C9851A",
                strokeWidth=2.5,
                point=alt.OverlayMarkDef(
                    filled=True,
                    size=55,
                ),
            )
            .encode(
                x=alt.X(
                    "mes:N",
                    title=None,
                    sort=None,
                    axis=alt.Axis(
                        labelAngle=0,
                        grid=False,
                    ),
                ),

                y=alt.Y(
                    "unseen_item_rate:Q",
                    title="Unseen rate (%)",
                    scale=alt.Scale(
                        zero=False
                    ),
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "mes:N",
                        title="Mês",
                    ),

                    alt.Tooltip(
                        "n:Q",
                        title="Observações",
                    ),

                    alt.Tooltip(
                        "unseen_item_rate:Q",
                        title="Unseen rate",
                        format=".2f",
                    ),

                    alt.Tooltip(
                        "mae_log:Q",
                        title="MAE log",
                        format=".4f",
                    ),
                ],
            )
            .properties(
                title="Unseen rate mensal",
                height=290,
            )
        )

        st.altair_chart(
            monthly_unseen_chart,
            use_container_width=True,
        )

    # ========================================================
    # KNOWN VS UNSEEN
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-title">'
        'Known vs Unseen'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Separação entre itens com histórico conhecido '
        'e casos de cold start.'
        '</div>',
        unsafe_allow_html=True,
    )

    cold_plot = cold.copy()

    cold_plot["Ano"] = (
        cold_plot["ano"]
        .astype(str)
    )

    cold_plot["Segmento"] = (
        cold_plot["status"]
        .map(
            {
                "known": "Known",
                "unseen": "Unseen",
            }
        )
    )

    cold_chart = (
        alt.Chart(
            cold_plot
        )
        .mark_bar(
            cornerRadiusTopLeft=3,
            cornerRadiusTopRight=3,
        )
        .encode(
            x=alt.X(
                "Segmento:N",
                title=None,
                axis=alt.Axis(
                    labelAngle=0,
                ),
            ),

            xOffset="Ano:N",

            y=alt.Y(
                "mae_log:Q",
                title="MAE log",
                scale=alt.Scale(
                    zero=True
                ),
                axis=alt.Axis(
                    grid=True,
                    gridColor="#EEF0F3",
                ),
            ),

            color=alt.Color(
                "Ano:N",
                title="Período",
                scale=alt.Scale(
                    domain=[
                        "2025",
                        "2026",
                    ],
                    range=[
                        "#9AA0A6",
                        "#5B0011",
                    ],
                ),
            ),

            tooltip=[
                alt.Tooltip(
                    "Ano:N",
                    title="Ano",
                ),

                alt.Tooltip(
                    "Segmento:N",
                    title="Segmento",
                ),

                alt.Tooltip(
                    "n:Q",
                    title="Observações",
                ),

                alt.Tooltip(
                    "mae_log:Q",
                    title="MAE log",
                    format=".4f",
                ),

                alt.Tooltip(
                    "medape:Q",
                    title="MedAPE",
                    format=".2f",
                ),

                alt.Tooltip(
                    "wape:Q",
                    title="WAPE",
                    format=".2f",
                ),
            ],
        )
        .properties(
            height=300,
        )
    )

    st.altair_chart(
        cold_chart,
        use_container_width=True,
    )

    st.caption(
        "Itens unseen apresentam erro superior aos itens "
        "known. O aumento da participação unseen em 2026 "
        "é relevante para a leitura da performance global."
    )

    # ========================================================
    # PERFORMANCE POR CATEGORIA
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-title">'
        'Performance e drift por categoria'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="pi-section-subtitle">'
        'Comparação de erro e mudança no mix entre '
        'validação 2025 e OOT 2026.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_category, col_mix = (
        st.columns(2)
    )

    # --------------------------------------------------------
    # MAE categoria
    # --------------------------------------------------------

    with col_category:

        category_long = (
            category[
                [
                    "categoria_relevante",
                    "mae_log_2025",
                    "mae_log_2026",
                ]
            ]
            .melt(
                id_vars=[
                    "categoria_relevante"
                ],
                value_vars=[
                    "mae_log_2025",
                    "mae_log_2026",
                ],
                var_name="periodo",
                value_name="mae_log",
            )
        )

        category_long[
            "Periodo"
        ] = (
            category_long[
                "periodo"
            ]
            .map(
                {
                    "mae_log_2025":
                        "2025",

                    "mae_log_2026":
                        "2026",
                }
            )
        )

        category_chart = (
            alt.Chart(
                category_long
            )
            .mark_bar(
                cornerRadiusEnd=3
            )
            .encode(
                x=alt.X(
                    "mae_log:Q",
                    title="MAE log",
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                y=alt.Y(
                    "categoria_relevante:N",
                    title=None,
                    sort=alt.SortField(
                        field="mae_log",
                        order="descending",
                    ),
                    axis=alt.Axis(
                        labelLimit=190,
                        domain=False,
                        ticks=False,
                    ),
                ),

                yOffset="Periodo:N",

                color=alt.Color(
                    "Periodo:N",
                    title="Período",
                    scale=alt.Scale(
                        domain=[
                            "2025",
                            "2026",
                        ],
                        range=[
                            "#9AA0A6",
                            "#5B0011",
                        ],
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "categoria_relevante:N",
                        title="Categoria",
                    ),

                    alt.Tooltip(
                        "Periodo:N",
                        title="Período",
                    ),

                    alt.Tooltip(
                        "mae_log:Q",
                        title="MAE log",
                        format=".4f",
                    ),
                ],
            )
            .properties(
                title="MAE log por categoria",
                height=330,
            )
        )

        st.altair_chart(
            category_chart,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Mudanca de mix
    # --------------------------------------------------------

    with col_mix:

        mix_plot = (
            mix
            .sort_values(
                "abs_delta_pp",
                ascending=False,
            )
            .copy()
        )

        mix_plot[
            "Direção"
        ] = (
            mix_plot[
                "delta_pp"
            ]
            .apply(
                lambda x:
                    "Aumento"
                    if x >= 0
                    else "Redução"
            )
        )

        mix_chart = (
            alt.Chart(
                mix_plot
            )
            .mark_bar(
                cornerRadiusEnd=3
            )
            .encode(
                x=alt.X(
                    "delta_pp:Q",
                    title=(
                        "Mudança de participação (p.p.)"
                    ),
                    axis=alt.Axis(
                        grid=True,
                        gridColor="#EEF0F3",
                    ),
                ),

                y=alt.Y(
                    "categoria_relevante:N",
                    title=None,
                    sort=alt.SortField(
                        field="abs_delta_pp",
                        order="descending",
                    ),
                    axis=alt.Axis(
                        labelLimit=190,
                        domain=False,
                        ticks=False,
                    ),
                ),

                color=alt.Color(
                    "Direção:N",
                    title=None,
                    scale=alt.Scale(
                        domain=[
                            "Aumento",
                            "Redução",
                        ],
                        range=[
                            "#C9851A",
                            "#2B6CB0",
                        ],
                    ),
                ),

                tooltip=[
                    alt.Tooltip(
                        "categoria_relevante:N",
                        title="Categoria",
                    ),

                    alt.Tooltip(
                        "share_2025_pct:Q",
                        title="Share 2025",
                        format=".2f",
                    ),

                    alt.Tooltip(
                        "share_2026_pct:Q",
                        title="Share 2026",
                        format=".2f",
                    ),

                    alt.Tooltip(
                        "delta_pp:Q",
                        title="Δ p.p.",
                        format="+.2f",
                    ),
                ],
            )
            .properties(
                title="Mudança no mix de categorias",
                height=330,
            )
        )

        st.altair_chart(
            mix_chart,
            use_container_width=True,
        )

        st.caption(
            (
                "Total Variation Distance do mix: "
                f"{category_tvd:.2f}%"
            ).replace(".", ",")
        )

    # ========================================================
    # TABELA DE DIAGNOSTICO
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    with st.expander(
        "Detalhamento por categoria"
    ):

        category_table = (
            category[
                [
                    "categoria_relevante",
                    "n_2025",
                    "n_2026",
                    "mae_log_2025",
                    "mae_log_2026",
                    "delta_mae_log_pct",
                    "unseen_item_rate_2025",
                    "unseen_item_rate_2026",
                ]
            ]
            .sort_values(
                "mae_log_2026",
                ascending=False,
            )
            .rename(
                columns={
                    "categoria_relevante":
                        "Categoria",

                    "n_2025":
                        "N 2025",

                    "n_2026":
                        "N 2026",

                    "mae_log_2025":
                        "MAE 2025",

                    "mae_log_2026":
                        "MAE 2026",

                    "delta_mae_log_pct":
                        "Delta MAE (%)",

                    "unseen_item_rate_2025":
                        "Unseen 2025 (%)",

                    "unseen_item_rate_2026":
                        "Unseen 2026 (%)",
                }
            )
        )

        st.dataframe(
            category_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "MAE 2025":
                    st.column_config.NumberColumn(
                        format="%.4f"
                    ),

                "MAE 2026":
                    st.column_config.NumberColumn(
                        format="%.4f"
                    ),

                "Delta MAE (%)":
                    st.column_config.NumberColumn(
                        format="%+.2f%%"
                    ),

                "Unseen 2025 (%)":
                    st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),

                "Unseen 2026 (%)":
                    st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),
            },
        )


# ============================================================
# METHODOLOGY
# ============================================================

if pagina == "Methodology":

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