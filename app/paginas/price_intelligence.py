"""Pagina: price_intelligence. Extraido de app/dashboard.py na Fase 15.5."""
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

