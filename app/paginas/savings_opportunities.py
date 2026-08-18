"""Pagina: savings_opportunities. Extraido de app/dashboard.py na Fase 15.5."""
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

