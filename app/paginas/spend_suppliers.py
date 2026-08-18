"""Pagina: spend_suppliers. Extraido de app/dashboard.py na Fase 15.5."""
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
    # --------------------------------------------------------
    # Analises globais
    # --------------------------------------------------------

    spend_cat = dados["spend_by_category"]

    hhi_cat = dados["hhi_by_category"]

    abc_global = dados["supplier_abc_by_category"][
        dados["supplier_abc_by_category"]["categoria_relevante"]
        == "__GLOBAL__"
    ].copy()

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

    abc = dados["supplier_abc_by_category"][
        dados["supplier_abc_by_category"]["categoria_relevante"]
        == categoria_selecionada
    ].copy()

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

