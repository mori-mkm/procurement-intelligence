"""
Transformação Silver -> Gold: modelo dimensional.
Fase 4. Ver docs/adr/ para decisões de grão, chaves e limitações conhecidas.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Nota de design: _strip_accents tem underscore (convenção de "privado" do
# módulo silver.py), mas reaproveitamos aqui em vez de duplicar a lógica.
# Frágil por natureza -- se silver.py remover/renomear essa função no
# futuro, gold.py quebra. Candidato a promover para função pública
# compartilhada quando mexermos em silver.py de novo.
from src.transformation.silver import classify_unit_comparability, _strip_accents


# Campos do cabeçalho (VW_FT_PNCP_COMPRA) que compõem dim_buyer.
# orgao_subrogado_* NÃO é usado: investigação (Fase 4) mostrou que, nos
# casos observados, é sempre a mesma entidade que orgao_entidade_*, apenas
# com o CNPJ mal tipado na fonte (perda de zero à esquerda). Não há
# evidência de sub-rogação real (compra em nome de terceiro) nos dados
# analisados até aqui.
COLUNAS_DIM_BUYER = [
    "id_compra",
    "orgao_entidade_cnpj",
    "orgao_entidade_razao_social",
    "unidade_orgao_uf_sigla",
    "unidade_orgao_municipio_nome",
    "codigo_modalidade",
    "modalidade_nome",
]


def build_dim_buyer(df_cabecalho: pd.DataFrame) -> pd.DataFrame:
    """Constrói dim_buyer a partir do Bronze de cabeçalho (VW_FT_PNCP_COMPRA),
    já carregado via load_bronze_csv (tipagem de ID já resolvida).

    Grão: 1 linha por id_compra. Não deduplica nem valida aqui — isso é
    responsabilidade de quem ingeriu (id_compra já confirmado único na
    investigação da Fase 4, mas não assumimos isso silenciosamente para
    sempre; ver validate_dim_buyer_grain).
    """
    colunas_disponiveis = [c for c in COLUNAS_DIM_BUYER if c in df_cabecalho.columns]
    faltando = set(COLUNAS_DIM_BUYER) - set(colunas_disponiveis)
    if faltando:
        raise ValueError(f"Colunas esperadas ausentes no cabeçalho: {faltando}")

    return df_cabecalho[colunas_disponiveis].copy()


def validate_dim_buyer_grain(dim_buyer: pd.DataFrame) -> dict[str, Any]:
    """Confirma que id_compra é único em dim_buyer — não assume, mede."""
    n_total = len(dim_buyer)
    n_duplicado = int(dim_buyer["id_compra"].duplicated().sum())
    return {
        "n_linhas": n_total,
        "id_compra_duplicado": n_duplicado,
        "grao_valido": n_duplicado == 0,
    }


def join_fact_with_buyer(df_fact_item: pd.DataFrame, dim_buyer: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Junta o Silver de item (grão id_compra_item x cod_fornecedor) com
    dim_buyer (grão id_compra) via id_compra. Left join -- preserva todas
    as linhas de item mesmo se o cabeçalho correspondente não tiver sido
    ingerido (caso esperado: cobertura de cabeçalho pode ser menor que a
    de item, já que ingerimos os dois separadamente).
    """
    if "id_compra" not in df_fact_item.columns:
        raise ValueError("df_fact_item precisa ter a coluna id_compra para o join")

    n_antes = len(df_fact_item)
    resultado = df_fact_item.merge(
        dim_buyer, on="id_compra", how="left", suffixes=("", "_buyer")
    )
    n_depois = len(resultado)

    n_sem_match = int(resultado["unidade_orgao_uf_sigla"].isna().sum())

    stats = {
        "linhas_fact_antes": n_antes,
        "linhas_apos_join": n_depois,
        "linhas_sem_match_no_buyer": n_sem_match,
        "pct_sem_match": round(100 * n_sem_match / n_antes, 4) if n_antes else 0.0,
    }

    if n_depois != n_antes:
        stats["aviso"] = "Join alterou contagem de linhas — dim_buyer pode ter id_compra duplicado. Investigar antes de confiar no resultado."

    return resultado, stats


def resolve_duplicate_buyer_records(
    df_cabecalho: pd.DataFrame, date_col: str = "data_publicacao_pncp"
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Resolve id_compra duplicado no cabeçalho combinado multi-ano.

    Dois fenômenos observados (Fase 4, investigação real): (1) duplicata
    dentro do mesmo arquivo anual, causa não identificada com certeza,
    concentrada em 2024; (2) sobreposição entre arquivos anuais adjacentes
    (compra publicada perto da virada do ano aparece nos dois snapshots).

    Critério: mantém a linha com data_publicacao_pncp mais recente por
    id_compra. Não é o critério ideal (não temos data_atualizacao_pncp
    populada nos casos observados para desempate mais preciso), mas é o
    único campo disponível e consistentemente preenchido nos casos vistos.
    """
    n_antes = len(df_cabecalho)
    n_ids_distintos_antes = df_cabecalho["id_compra"].nunique()

    df_resolvido = (
        df_cabecalho.sort_values(date_col, ascending=False)
        .drop_duplicates(subset="id_compra", keep="first")
        .reset_index(drop=True)
    )

    stats = {
        "linhas_antes": n_antes,
        "linhas_depois": len(df_resolvido),
        "duplicatas_removidas": n_antes - len(df_resolvido),
        "id_compra_distintos": n_ids_distintos_antes,
    }
    return df_resolvido, stats


def load_dim_buyer_from_annual(anos: list[int]) -> pd.DataFrame:
    """Constrói dim_buyer a partir dos Parquets anuais já materializados
    (src/ingestion/pncp_bulk_annual.py), cobrindo múltiplos anos. Resolve a
    lacuna de cobertura da Fase 4: item diário referencia id_compra de
    datas de publicação muito anteriores ao dia do snapshot de cabeçalho.

    Também resolve id_compra duplicado entre/dentro dos arquivos anuais
    (ver resolve_duplicate_buyer_records) antes de montar o dim_buyer final.
    """
    from src.ingestion.pncp_bulk_annual import local_parquet_path, DATASET_COMPRA

    frames = []
    for ano in anos:
        caminho = local_parquet_path(ano, DATASET_COMPRA)
        if not caminho.exists():
            raise FileNotFoundError(
                f"Parquet anual não encontrado para {ano}: {caminho}. "
                f"Rode: python -m src.ingestion.pncp_bulk_annual {ano} {DATASET_COMPRA}"
            )
        frames.append(pd.read_parquet(caminho))

    df_completo = pd.concat(frames, ignore_index=True)
    df_completo["data_publicacao_pncp"] = pd.to_datetime(df_completo["data_publicacao_pncp"], errors="coerce")
    df_resolvido, _ = resolve_duplicate_buyer_records(df_completo)
    return build_dim_buyer(df_resolvido)


# Correções pontuais de erros tipográficos conhecidos na fonte.
# Cada entrada aqui foi CONFIRMADA manualmente em dado real (Fase 4) —
# não é regra automática de fusão por similaridade. Aplica-se apenas à
# construção de item_key (chave derivada); descricao_resumida (fato
# observado) permanece intocada. Chaves já normalizadas (lowercase, sem
# acento), aplicadas depois de strip_accents().lower().
CORRECOES_TIPOGRAFICAS_CONHECIDAS = {
    "desaude": "de saude",
    # Adicionar novos casos aqui, um de cada vez, só com evidência
    # confirmada em dado real -- não adivinhar padrões.
}


def _apply_known_typo_corrections(texto: str) -> str:
    """Aplica correções pontuais com borda de palavra (\\b) -- mesma cautela
    já usada nas palavras-chave de categoria (ADR-0009), para evitar
    substituir um trecho no meio de outra palavra por coincidência."""
    for errado, certo in CORRECOES_TIPOGRAFICAS_CONHECIDAS.items():
        texto = re.sub(rf"\b{re.escape(errado)}\b", certo, texto)
    return texto


def normalize_item_key(texto) -> str | None:
    """Normaliza descricao_resumida para chave de item (ADR-0006):
    lowercase, remove acentuação, corrige erros tipográficos conhecidos
    (ver CORRECOES_TIPOGRAFICAS_CONHECIDAS), colapsa espaços.

    Correções são uma LISTA CURADA, não fusão automática por similaridade —
    cada entrada exige evidência manual confirmada. descricao_resumida
    original (fato observado) nunca é alterada, só a chave derivada."""
    if pd.isna(texto):
        return None
    limpo = _strip_accents(str(texto)).lower()
    limpo = _apply_known_typo_corrections(limpo)
    limpo = re.sub(r"\s+", " ", limpo).strip()
    return limpo or None


def build_dim_item(df_fact: pd.DataFrame) -> pd.DataFrame:
    """Constrói dim_item. Grão: item_key (descrição normalizada, ADR-0006)
    — não CATMAT, que tem 52-81% de nulos (ADR-0006) e, quando presente,
    pode ser inconsistente sob a mesma descrição (ex: "Fruta" -> 36 CATMATs
    distintos, achado da Fase 4).

    cod_item_catalogo_mais_frequente é enriquecimento, não chave.
    n_catmats_distintos_observados sinaliza ambiguidade em vez de escondê-la.

    unit_flag é computado aqui (nível Gold, sobre todos os dias disponíveis
    em df_fact), não no Silver diário — dá mais poder estatístico à
    detecção de heterogeneidade de unidade (mais transações por item) do
    que recalcular a cada dia isoladamente. classify_unit_comparability
    (ADR-0005/0006) estava pendente de integração; entra aqui pela
    primeira vez.
    """
    df = df_fact.copy()
    df["item_key"] = df["descricao_resumida"].apply(normalize_item_key)
    df = df[df["item_key"].notna()].copy()

    df = classify_unit_comparability(df, item_col="item_key", unit_col="unidade_medida")

    def moda_ou_none(serie: pd.Series):
        s = serie.dropna()
        return s.mode().iloc[0] if not s.empty else None

    registros = []
    for item_key, grupo in df.groupby("item_key"):
        catmats_validos = grupo["cod_item_catalogo"].dropna() if "cod_item_catalogo" in grupo.columns else pd.Series(dtype=object)
        registros.append({
            "item_key": item_key,
            "descricao_resumida_amostra": grupo["descricao_resumida"].mode().iloc[0],
            "material_ou_servico_nome": moda_ou_none(grupo["material_ou_servico_nome"]) if "material_ou_servico_nome" in grupo.columns else None,
            "unit_flag": grupo["unit_flag"].iloc[0],  # determinístico por grupo, ver classify_unit_comparability
            "categoria_relevante": moda_ou_none(grupo["categoria_relevante"]) if "categoria_relevante" in grupo.columns else None,
            "cod_item_catalogo_mais_frequente": catmats_validos.mode().iloc[0] if not catmats_validos.empty else None,
            "n_catmats_distintos_observados": int(catmats_validos.nunique()),
            "n_transacoes": len(grupo),
        })

    return pd.DataFrame(registros).sort_values("n_transacoes", ascending=False).reset_index(drop=True)


def build_dim_supplier(df_fact: pd.DataFrame) -> pd.DataFrame:
    """Constrói dim_supplier. Grão: cod_fornecedor. Sem porte/CNAE — esses
    campos não existem no bulk CSV; enriquecimento via Receita Federal CNPJ
    fica pendente (Fase 0, Seção 8, Ajuste 2).

    n_produtos_servicos_distintos conta item_key distinto, não
    id_compra_item — contar id_compra_item seria redundante com
    n_transacoes, já que o grão da Silver garante 1 linha por
    (id_compra_item, cod_fornecedor).

    Nota de eficiência: recalcula item_key aqui, independente de
    build_dim_item — redundante, mas mantém cada função autocontida. Se
    isso incomodar performance quando o volume crescer, dá para calcular
    item_key uma vez no df_fact consolidado antes de chamar as duas
    funções (ponto a revisitar ao montar fact_purchase).
    """
    df = df_fact[df_fact["cod_fornecedor"].notna()].copy()
    df["_item_key_tmp"] = df["descricao_resumida"].apply(normalize_item_key)

    registros = []
    for cnpj, grupo in df.groupby("cod_fornecedor"):
        registros.append({
            "supplier_key": cnpj,
            "nome_fornecedor": grupo["nome_fornecedor"].mode().iloc[0] if grupo["nome_fornecedor"].notna().any() else None,
            "n_transacoes": len(grupo),
            "n_produtos_servicos_distintos": int(grupo["_item_key_tmp"].nunique()),
        })

    return pd.DataFrame(registros).sort_values("n_transacoes", ascending=False).reset_index(drop=True)


MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def build_dim_date(data_inicio, data_fim) -> pd.DataFrame:
    """Dimensão de calendário padrão, cobrindo [data_inicio, data_fim]
    (datetime.date). Independente da fato — construída por range, não a
    partir de datas observadas no dado."""
    datas = pd.date_range(data_inicio, data_fim, freq="D")
    return pd.DataFrame({
        "date_key": datas.strftime("%Y%m%d").astype(int),
        "data": datas,
        "ano": datas.year,
        "trimestre": datas.quarter,
        "mes": datas.month,
        "dia": datas.day,
        "dia_semana": datas.dayofweek,
        "nome_mes": datas.month.map(MESES_PT),
    })


def build_fact_purchase(
    df_item_silver: pd.DataFrame, dim_buyer: pd.DataFrame, dim_item: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Monta fact_purchase final (Fase 4): une Silver de item com dim_buyer
    (join_fact_with_buyer) e dim_item (item_key -> unit_flag,
    cod_item_catalogo_mais_frequente -- calculados uma única vez em
    build_dim_item, não recomputados aqui, para não criar duas fontes de
    verdade divergentes para o mesmo item).

    Filtra itens sem resultado homologado (valor_unitario_resultado nulo)
    ANTES de montar o fato -- ~57% do Silver combinado (Fase 4, achado real)
    são itens ainda em andamento (tem_resultado=False), sem preço/quantidade/
    data de resultado. fact_purchase representa transações realizadas; itens
    em andamento continuam disponíveis no Silver, só não entram no fato.

    Grão: (purchase_item_id, supplier_key) -- ADR-0004. Exceções conhecidas
    e flagadas (resultado_conflitante=True, ADR-0010) podem violar esse
    grão intencionalmente; qualquer violação NÃO flagada é inesperada
    (ver validate_fact_purchase_grain).

    Usa valor_unitario_resultado/valor_total_resultado/quantidade_resultado
    (preço efetivamente homologado), não os campos _estimado (estimativa
    pré-licitação) -- distinção já estabelecida no ADR-0010.

    real_unit_price fica None -- deflação por IPCA é pendência documentada
    desde a Fase 0, ainda não implementada.
    """
    if "descricao_resumida" not in df_item_silver.columns:
        raise ValueError("df_item_silver precisa ter descricao_resumida para calcular item_key")

    n_antes_filtro = len(df_item_silver)
    df_item_silver = df_item_silver[df_item_silver["valor_unitario_resultado"].notna()].copy()
    n_excluidos_sem_resultado = n_antes_filtro - len(df_item_silver)

    df = df_item_silver.copy()
    df["item_key"] = df["descricao_resumida"].apply(normalize_item_key)

    df_com_buyer, stats_join_buyer = join_fact_with_buyer(df, dim_buyer)

    colunas_dim_item = ["item_key", "unit_flag", "cod_item_catalogo_mais_frequente"]
    colunas_disponiveis = [c for c in colunas_dim_item if c in dim_item.columns]
    df_final = df_com_buyer.merge(dim_item[colunas_disponiveis], on="item_key", how="left")

    date_key_str = pd.to_datetime(df_final["data_resultado"], errors="coerce").dt.strftime("%Y%m%d")
    df_final["date_key"] = pd.to_numeric(date_key_str, errors="coerce").astype("Int64")

    fact = pd.DataFrame({
        "purchase_item_id": df_final["id_compra_item"],
        "supplier_key": df_final["cod_fornecedor"],
        "item_key": df_final["item_key"],
        "buyer_key": df_final.get("orgao_entidade_cnpj"),
        "unidade_orgao_uf_sigla": df_final.get("unidade_orgao_uf_sigla"),
        "modalidade_nome": df_final.get("modalidade_nome"),
        "date_key": df_final["date_key"],
        "quantity": df_final.get("quantidade_resultado"),
        "unit_price": df_final.get("valor_unitario_resultado"),
        "total_price": df_final.get("valor_total_resultado"),
        "real_unit_price": pd.NA,  # pendente: deflação IPCA (Fase 0)
        "categoria_relevante": df_final.get("categoria_relevante"),
        "unit_flag": df_final.get("unit_flag"),
        "resultado_conflitante": df_final.get("resultado_conflitante"),
        "cod_item_catalogo_mais_frequente": df_final.get("cod_item_catalogo_mais_frequente"),
    })

    stats = {
        "n_linhas": len(fact),
        "join_buyer": stats_join_buyer,
        "n_excluidos_sem_resultado_homologado": n_excluidos_sem_resultado,
        "n_sem_item_key": int(fact["item_key"].isna().sum()),
        "n_sem_date_key": int(fact["date_key"].isna().sum()),
    }
    return fact, stats


def validate_fact_purchase_grain(df_fact: pd.DataFrame) -> dict[str, Any]:
    """Valida grão (purchase_item_id, supplier_key) -- ADR-0004. Separa
    violações ESPERADAS (já flagadas resultado_conflitante=True, ADR-0010)
    de violações INESPERADAS -- essas últimas merecem investigação, não
    devem simplesmente ser toleradas."""
    chave = ["purchase_item_id", "supplier_key"]
    duplicado_mask = df_fact.duplicated(subset=chave, keep=False)
    n_violacoes_totais = int(df_fact.duplicated(subset=chave, keep="first").sum())

    if "resultado_conflitante" in df_fact.columns and duplicado_mask.any():
        grupos_nao_flagados = (
            df_fact[duplicado_mask]
            .groupby(chave)["resultado_conflitante"]
            .apply(lambda s: not s.any())
        )
        n_grupos_inesperados = int(grupos_nao_flagados.sum())
    else:
        n_grupos_inesperados = 0

    return {
        "grao": chave,
        "n_linhas": len(df_fact),
        "n_violacoes_totais": n_violacoes_totais,
        "n_grupos_violacao_nao_flagados": n_grupos_inesperados,
        "grao_valido_considerando_flags": n_grupos_inesperados == 0,
    }