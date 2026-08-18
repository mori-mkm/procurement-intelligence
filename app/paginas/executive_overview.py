"""Pagina: executive_overview. Extraido de app/dashboard.py na Fase 15.5."""
from textwrap import dedent
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
    # BASE EXECUTIVA
    # ========================================================

    spend_relevante = dados["spend_by_category"]

    hhi_relevante = dados["hhi_by_category"]

    fornecedores_relevantes = dados["supplier_abc_by_category"][
        dados["supplier_abc_by_category"]["categoria_relevante"]
        == "__GLOBAL__"
    ].copy()

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

