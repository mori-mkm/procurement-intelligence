"""Pagina: model_monitoring. Extraido de app/dashboard.py na Fase 15.5."""
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

