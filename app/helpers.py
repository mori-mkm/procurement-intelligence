"""Funcoes auxiliares compartilhadas entre paginas do dashboard.
Extraido de app/dashboard.py na Fase 15.5.
"""
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

from src.transformation.gold import load_gold_layer
from src.analytics.dashboard_data import load_dashboard_artifacts


def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()

    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai

    raise RuntimeError("Nao encontrei a raiz do projeto")


RAIZ = achar_raiz_projeto(Path(__file__))
sys.path.insert(0, str(RAIZ))


import altair as alt


def _tema_procurement_intelligence():
    return {
        "config": {
            "background": "#FFFFFF",
            "view": {"fill": "#FFFFFF", "stroke": "transparent"},
            "axis": {
                "domainColor": "#E9E9EE",
                "gridColor": "#E9E9EE",
                "labelColor": "#1F2024",
                "titleColor": "#1F2024",
                "tickColor": "#E9E9EE",
            },
            "legend": {"labelColor": "#1F2024", "titleColor": "#1F2024"},
            "title": {"color": "#1F2024"},
        }
    }


alt.themes.register("procurement_intelligence", _tema_procurement_intelligence)
alt.themes.enable("procurement_intelligence")
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

    try:
        gold = load_gold_layer()
        gold_disponivel = True
    except FileNotFoundError:
        gold = {"fact_purchase": None, "dim_supplier": None}
        gold_disponivel = False

    artifacts = load_dashboard_artifacts(
        RAIZ
    )

    return {
    "fact": gold["fact_purchase"],
    "dim_supplier": gold["dim_supplier"],
    "gold_disponivel": gold_disponivel,
    **artifacts,
    }
