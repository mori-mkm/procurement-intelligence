import pandas as pd

from src.analytics.savings_engine import compute_savings_opportunity, rank_savings_by_category, summarize_savings


def make_anomalias_df():
    return pd.DataFrame({
        "item_key": ["limpeza", "limpeza", "consultoria"],
        "categoria_relevante": ["Limpeza / Facilities", "Limpeza / Facilities", "Consultoria / Servicos Profissionais"],
        "unit_price": [59398.48, 100.0, 3_600_000.0],
        "preco_esperado": [19.04, 90.0, 5535.94],
        "quantity": [1.0, 5.0, 1.0],
        "anomaly_direction": ["acima_do_esperado", "acima_do_esperado", "acima_do_esperado"],
    })


def test_compute_savings_opportunity_flags_high_ticket():
    df = compute_savings_opportunity(make_anomalias_df())
    assert df["ticket_alto_cautela"].iloc[0] == True   # consultoria, apos sort
    assert (df["rotulo"] == "Potential Savings Opportunity").all()


def test_rank_savings_by_category_aggregates():
    df = compute_savings_opportunity(make_anomalias_df())
    ranking = rank_savings_by_category(df)
    assert len(ranking) == 2
    assert ranking["n_oportunidades"].sum() == 3


def test_summarize_savings_separates_high_ticket():
    df = compute_savings_opportunity(make_anomalias_df())
    resumo = summarize_savings(df)
    assert resumo["savings_potencial_excluindo_ticket_alto"] < resumo["savings_potencial_total"]
