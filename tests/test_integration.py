"""
Teste de integração: Bronze -> Silver -> Gold de ponta a ponta.

Cobre, num único conjunto de dados sintético pequeno, os 5 fenômenos reais
identificados nas Fases 2-4: deduplicação exata (ADR-0004), revisão
temporal (ADR-0004), conflito de mesma data (ADR-0010), join parcial de
comprador (Fase 4), e exclusão de itens sem resultado homologado
(ADR-0012). Não depende de rede nem de arquivos previamente baixados --
roda em qualquer máquina, a qualquer momento.
"""
import pandas as pd

from src.quality.checks import load_bronze_csv
from src.transformation.silver import build_silver_transformation_report
from src.transformation.gold import (
    build_dim_buyer,
    validate_dim_buyer_grain,
    build_dim_item,
    build_fact_purchase,
    validate_fact_purchase_grain,
)


def make_item_bronze_df() -> pd.DataFrame:
    linhas = [
        # --- Caso A: Notebook Dell -- duplicata exata (2 linhas -> 1) ---
        dict(id_compra_item="A0000000000000001", cod_fornecedor="F0000000000000001",
             nome_fornecedor="Fornecedor A", cod_item_catalogo="111111",
             descricao_resumida="Notebook Dell", material_ou_servico_nome="Material",
             unidade_medida="Unidade", quantidade=10, quantidade_resultado=10,
             valor_unitario_estimado=3000.0, valor_unitario_resultado=2900.0,
             valor_total=30000.0, valor_total_resultado=29000.0,
             data_inclusao_pncp="2025-01-01", data_atualizacao_pncp="2025-01-02",
             data_resultado="2025-01-02", id_compra="1111111111111111",
             orgao_entidade_cnpj="00394502000144",
             COD_RESULTADO_ITEM="R000001", srk_pncp_item_compra="S000001"),
        dict(id_compra_item="A0000000000000001", cod_fornecedor="F0000000000000001",
             nome_fornecedor="Fornecedor A", cod_item_catalogo="111111",
             descricao_resumida="Notebook Dell", material_ou_servico_nome="Material",
             unidade_medida="Unidade", quantidade=10, quantidade_resultado=10,
             valor_unitario_estimado=3000.0, valor_unitario_resultado=2900.0,
             valor_total=30000.0, valor_total_resultado=29000.0,
             data_inclusao_pncp="2025-01-01", data_atualizacao_pncp="2025-01-02",
             data_resultado="2025-01-02", id_compra="1111111111111111",
             orgao_entidade_cnpj="00394502000144",
             COD_RESULTADO_ITEM="R000002", srk_pncp_item_compra="S000002"),

        # --- Caso B: Mouse Optico -- revisao temporal (2 linhas -> 1, mais recente) ---
        dict(id_compra_item="B0000000000000001", cod_fornecedor="F0000000000000002",
             nome_fornecedor="Fornecedor B", cod_item_catalogo=None,
             descricao_resumida="Mouse Optico", material_ou_servico_nome="Material",
             unidade_medida="Unidade", quantidade=5, quantidade_resultado=5,
             valor_unitario_estimado=55.0, valor_unitario_resultado=50.0,
             valor_total=275.0, valor_total_resultado=250.0,
             data_inclusao_pncp="2025-01-01", data_atualizacao_pncp="2025-01-01",
             data_resultado="2025-01-01", id_compra="1111111111111111",
             orgao_entidade_cnpj="00394502000144",
             COD_RESULTADO_ITEM="R000003", srk_pncp_item_compra="S000003"),
        dict(id_compra_item="B0000000000000001", cod_fornecedor="F0000000000000002",
             nome_fornecedor="Fornecedor B", cod_item_catalogo=None,
             descricao_resumida="Mouse Optico", material_ou_servico_nome="Material",
             unidade_medida="Unidade", quantidade=5, quantidade_resultado=5,
             valor_unitario_estimado=55.0, valor_unitario_resultado=55.0,
             valor_total=275.0, valor_total_resultado=275.0,
             data_inclusao_pncp="2025-01-01", data_atualizacao_pncp="2025-01-05",
             data_resultado="2025-01-05", id_compra="1111111111111111",
             orgao_entidade_cnpj="00394502000144",
             COD_RESULTADO_ITEM="R000004", srk_pncp_item_compra="S000004"),

        # --- Caso C: Consultoria TI -- mesma data, valor conflitante (2 linhas, ambas ficam) ---
        dict(id_compra_item="C0000000000000001", cod_fornecedor="F0000000000000003",
             nome_fornecedor="Fornecedor C", cod_item_catalogo=None,
             descricao_resumida="Consultoria TI", material_ou_servico_nome="Serviço",
             unidade_medida="Unidade", quantidade=1, quantidade_resultado=1,
             valor_unitario_estimado=200.0, valor_unitario_resultado=200.0,
             valor_total=200.0, valor_total_resultado=200.0,
             data_inclusao_pncp="2025-01-01", data_atualizacao_pncp="2025-01-03",
             data_resultado="2025-01-03", id_compra="1111111111111111",
             orgao_entidade_cnpj="00394502000144",
             COD_RESULTADO_ITEM="R000005", srk_pncp_item_compra="S000005"),
        dict(id_compra_item="C0000000000000001", cod_fornecedor="F0000000000000003",
             nome_fornecedor="Fornecedor C", cod_item_catalogo=None,
             descricao_resumida="Consultoria TI", material_ou_servico_nome="Serviço",
             unidade_medida="Unidade", quantidade=1, quantidade_resultado=1,
             valor_unitario_estimado=200.0, valor_unitario_resultado=210.0,
             valor_total=200.0, valor_total_resultado=210.0,
             data_inclusao_pncp="2025-01-01", data_atualizacao_pncp="2025-01-03",
             data_resultado="2025-01-03", id_compra="1111111111111111",
             orgao_entidade_cnpj="00394502000144",
             COD_RESULTADO_ITEM="R000006", srk_pncp_item_compra="S000006"),

        # --- Caso D: Cadeira Escritorio -- id_compra sem cabecalho correspondente ---
        dict(id_compra_item="D0000000000000001", cod_fornecedor="F0000000000000004",
             nome_fornecedor="Fornecedor D", cod_item_catalogo="222222",
             descricao_resumida="Cadeira Escritorio", material_ou_servico_nome="Material",
             unidade_medida="Unidade", quantidade=2, quantidade_resultado=2,
             valor_unitario_estimado=500.0, valor_unitario_resultado=480.0,
             valor_total=1000.0, valor_total_resultado=960.0,
             data_inclusao_pncp="2025-02-01", data_atualizacao_pncp="2025-02-02",
             data_resultado="2025-02-02", id_compra="3333333333333333",
             orgao_entidade_cnpj="00394502000144",
             COD_RESULTADO_ITEM="R000007", srk_pncp_item_compra="S000007"),

        # --- Caso E: Fruta -- ainda sem resultado homologado (excluido do fact) ---
        dict(id_compra_item="E0000000000000001", cod_fornecedor="F0000000000000005",
             nome_fornecedor=None, cod_item_catalogo=None,
             descricao_resumida="Fruta", material_ou_servico_nome="Material",
             unidade_medida="Quilograma", quantidade=100, quantidade_resultado=None,
             valor_unitario_estimado=5.0, valor_unitario_resultado=None,
             valor_total=500.0, valor_total_resultado=None,
             data_inclusao_pncp="2025-03-01", data_atualizacao_pncp="2025-03-01",
             data_resultado=None, id_compra="1111111111111111",
             orgao_entidade_cnpj="00394502000144",
             COD_RESULTADO_ITEM=None, srk_pncp_item_compra="S000008"),
    ]
    return pd.DataFrame(linhas)


def make_cabecalho_bronze_df() -> pd.DataFrame:
    # Só id_compra="1111111111111111" tem cabeçalho -- "3333333333333333"
    # (Caso D) fica sem match de propósito, para testar join parcial.
    return pd.DataFrame([
        dict(id_compra="1111111111111111", orgao_entidade_cnpj="00394502000144",
             orgao_entidade_razao_social="COMANDO DA MARINHA",
             unidade_orgao_uf_sigla="RJ", unidade_orgao_municipio_nome="Rio de Janeiro",
             codigo_modalidade=6, modalidade_nome="Pregão - Eletrônico"),
    ])


def test_full_pipeline_bronze_to_gold(tmp_path):
    caminho_item = tmp_path / "item.csv"
    caminho_cabecalho = tmp_path / "cabecalho.csv"
    make_item_bronze_df().to_csv(caminho_item, index=False)
    make_cabecalho_bronze_df().to_csv(caminho_cabecalho, index=False)

    # --- Bronze ---
    df_item_bronze = load_bronze_csv(caminho_item)
    df_cabecalho_bronze = load_bronze_csv(caminho_cabecalho)
    assert len(df_item_bronze) == 8

    # --- Silver ---
    relatorio_silver, df_item_silver = build_silver_transformation_report(df_item_bronze)
    assert relatorio_silver["deduplicacao"]["duplicatas_removidas"] == 1  # Caso A
    assert relatorio_silver["resolucao_revisoes_temporais"]["revisoes_temporais_resolvidas"] == 1  # Caso B
    assert relatorio_silver["resultado_conflitante"]["n_linhas_flagadas"] == 2  # Caso C
    assert len(df_item_silver) == 6

    # --- Gold: dim_buyer ---
    dim_buyer = build_dim_buyer(df_cabecalho_bronze)
    grao_buyer = validate_dim_buyer_grain(dim_buyer)
    assert grao_buyer["grao_valido"] is True

    # --- Gold: dim_item ---
    dim_item = build_dim_item(df_item_silver)
    assert len(dim_item) == 5  # notebook, mouse, consultoria, cadeira, fruta

    # --- Gold: fact_purchase ---
    fact, stats = build_fact_purchase(df_item_silver, dim_buyer, dim_item)
    assert stats["n_excluidos_sem_resultado_homologado"] == 1  # Caso E
    assert len(fact) == 5
    assert stats["join_buyer"]["linhas_sem_match_no_buyer"] == 1  # Caso D
    assert stats["n_sem_item_key"] == 0
    assert stats["n_sem_date_key"] == 0

    # --- Validação final de grão ---
    grao_fact = validate_fact_purchase_grain(fact)
    assert grao_fact["n_violacoes_totais"] == 1  # Caso C, esperado e flagado
    assert grao_fact["n_grupos_violacao_nao_flagados"] == 0
    assert grao_fact["grao_valido_considerando_flags"] is True

    # --- Checagens de conteúdo específico, não só contagem ---
    notebook = fact[fact["purchase_item_id"] == "A0000000000000001"]
    assert notebook["unit_price"].iloc[0] == 2900.0

    mouse = fact[fact["purchase_item_id"] == "B0000000000000001"]
    assert mouse["unit_price"].iloc[0] == 55.0  # ficou o valor mais recente, não o antigo (50.0)

    consultoria = fact[fact["purchase_item_id"] == "C0000000000000001"]
    assert len(consultoria) == 2
    assert set(consultoria["resultado_conflitante"]) == {True}

    cadeira = fact[fact["purchase_item_id"] == "D0000000000000001"]
    assert pd.isna(cadeira["unidade_orgao_uf_sigla"].iloc[0])  # sem match de cabeçalho, mas não quebrou
    assert cadeira["buyer_key"].iloc[0] == "00394502000144"  # esse campo vem do item, não do join

    assert "E0000000000000001" not in fact["purchase_item_id"].values  # Fruta excluída
