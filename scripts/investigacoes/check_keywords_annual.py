import duckdb
import re
import unicodedata

def strip_accents(texto):
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")

url_2025 = "https://repositorio.dados.gov.br/seges/comprasgov/anual/2025/comprasGOV-anual-VW_FT_PNCP_COMPRA_ITEM-2025.csv"

palavras = [
    "computador", "notebook", "software", "servidor de rede", "impressora",
    "monitor computador", "monitor de video", "storage", "firewall", "antivirus", "roteador",
    "telefonia", "link dedicado", "dados moveis", "central telefonica",
    "consultoria", "auditoria", "assessoria juridica", "advocaticio",
    "vigilancia patrimonial", "seguranca patrimonial", "cftv", "sistema de alarme",
    "servico de limpeza", "conservacao predial", "jardinagem", "dedetizacao", "manutencao predial",
    "mobiliario", "cadeira escritorio", "mesa escritorio", "material de escritorio",
    "locacao de veiculo", "locacao veicular", "aluguel de veiculo",
    "publicidade", "propaganda", "material grafico",
]
padrao_sql = "|".join(re.escape(p) for p in palavras)

query = f"""
    SELECT COUNT(*) AS total, SUM(CASE WHEN regexp_matches(
        lower(strip_accents(descricao_resumida)), '\\b({padrao_sql})\\b'
    ) THEN 1 ELSE 0 END) AS capturado
    FROM read_csv_auto('{url_2025}', ignore_errors=true)
"""
print("Testando sintaxe DuckDB para strip_accents/regexp_matches...")
try:
    resultado = con.execute(query).fetchone()
    print(f"Total: {resultado[0]:,} | Capturado: {resultado[1]:,} ({100*resultado[1]/resultado[0]:.2f}%)")
except Exception as e:
    print(f"Erro (esperado se DuckDB nao tiver strip_accents nativo): {e}")
