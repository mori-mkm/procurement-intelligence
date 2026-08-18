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



import sys as _sys
from pathlib import Path as _Path

def _achar_raiz(caminho_inicial):
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / '.git').exists():
            return pai
    raise RuntimeError('Nao encontrei a raiz do projeto')

_RAIZ = _achar_raiz(_Path(__file__).parent)
if str(_RAIZ) not in _sys.path:
    _sys.path.insert(0, str(_RAIZ))

import streamlit as st

from app.helpers import (
    achar_raiz_projeto,
    aplicar_design_system,
    carregar_dados_dashboard,
)

aplicar_design_system()
from app.paginas import (
    executive_overview,
    spend_suppliers,
    price_intelligence,
    savings_opportunities,
    model_monitoring,
    methodology,
)




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


PAGINAS_RENDER = {
    "Executive Overview": executive_overview.render,
    "Spend & Suppliers": spend_suppliers.render,
    "Price Intelligence": price_intelligence.render,
    "Savings Opportunities": savings_opportunities.render,
    "Model Monitoring": model_monitoring.render,
    "Methodology": methodology.render,
}

PAGINAS_RENDER[pagina](dados)
