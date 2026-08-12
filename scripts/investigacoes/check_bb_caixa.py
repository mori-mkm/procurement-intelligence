import duckdb

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")

BASE_BULK = "https://repositorio.dados.gov.br/seges/comprasgov"

for ano in [2024, 2025]:
    print(f"=== {ano}: busca por nome (razao social) no arquivo de cabecalho ===")
    url_compra = f"{BASE_BULK}/anual/{ano}/comprasGOV-anual-VW_FT_PNCP_COMPRA-{ano}.csv"

    query = f"""
        SELECT
            orgao_entidade_razao_social,
            orgao_subrogado_razao_social,
            COUNT(*) AS n_registros
        FROM read_csv_auto('{url_compra}', ignore_errors=true)
        WHERE orgao_entidade_razao_social ILIKE '%BANCO DO BRASIL%'
           OR orgao_entidade_razao_social ILIKE '%CAIXA ECON%'
           OR orgao_subrogado_razao_social ILIKE '%BANCO DO BRASIL%'
           OR orgao_subrogado_razao_social ILIKE '%CAIXA ECON%'
        GROUP BY orgao_entidade_razao_social, orgao_subrogado_razao_social
        ORDER BY n_registros DESC
    """
    try:
        resultado = con.execute(query).fetchall()
        if resultado:
            for entidade, subrogado, n in resultado:
                print(f"  {n} registros | entidade: {entidade} | subrogado: {subrogado}")
        else:
            print("  Nenhum registro encontrado por nome.")
    except Exception as e:
        print(f"  Erro: {e}")
    print()