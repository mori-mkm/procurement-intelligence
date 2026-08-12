from datetime import date
from src.ingestion.pncp_bulk import local_path_for
from src.quality.checks import load_bronze_csv
import pandas as pd
import re
import unicodedata

pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 200)

def strip_accents(texto):
    if pd.isna(texto):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c))

CATEGORIAS_TESTE = {
    "TI / Informatica": ["computador", "notebook", "software", "licenciamento de uso", "servidor de rede", "impressora", "monitor computador", "monitor de video", "storage", "firewall", "antivirus", "roteador"],
    "Telecom": ["telefonia", "link dedicado", "dados moveis", "central telefonica"],
    "Consultoria / Servicos Profissionais": ["consultoria", "auditoria", "assessoria juridica", "advocaticio"],
    "Seguranca / Vigilancia": ["vigilancia patrimonial", "seguranca patrimonial", "monitoramento eletronico", "cftv", "sistema de alarme"],
    "Limpeza / Facilities": ["servico de limpeza", "conservacao predial", "jardinagem", "dedetizacao", "manutencao predial"],
    "Mobiliario / Material de Escritorio": ["mobiliario", "cadeira escritorio", "mesa escritorio", "papel a4", "material de escritorio"],
    "Locacao de Veiculos": ["locacao de veiculo", "locacao veicular", "aluguel de veiculo", "locacao de frota"],
    "Marketing / Publicidade": ["publicidade", "propaganda", "material grafico"],
}

def compilar_padrao(palavras):
    escapadas = [re.escape(p) for p in palavras]
    # grupo nao-capturante (?:...) para eliminar o aviso do pandas
    return re.compile(r"\b(?:" + "|".join(escapadas) + r")\b", flags=re.IGNORECASE)

for dia in [date(2025, 12, 1), date(2026, 5, 22)]:
    print(f"=== {dia.isoformat()} ===")
    df = load_bronze_csv(local_path_for(dia))
    desc_original = df["descricao_resumida"].fillna("")
    desc_sem_acento = desc_original.apply(strip_accents)

    total_capturado = pd.Series(False, index=df.index)
    resultados_por_categoria = {}
    for categoria, palavras in CATEGORIAS_TESTE.items():
        padrao = compilar_padrao(palavras)
        mask = desc_sem_acento.str.contains(padrao)
        n = mask.sum()
        print(f"  {categoria}: {n} transacoes ({100*n/len(df):.2f}%)")
        total_capturado = total_capturado | mask
        resultados_por_categoria[categoria] = (padrao, mask)

    print(f"  TOTAL: {total_capturado.sum()} ({100*total_capturado.sum()/len(df):.2f}%)")
    print()
    print("  Amostra com contexto ao redor do match (texto ORIGINAL, com acento):")
    for categoria, (padrao, mask) in resultados_por_categoria.items():
        indices = df.loc[mask].index[:2]
        for idx in indices:
            texto_norm = desc_sem_acento.loc[idx]
            texto_orig = desc_original.loc[idx]
            match = padrao.search(texto_norm)
            inicio = max(0, match.start() - 30)
            fim = min(len(texto_orig), match.end() + 60)
            print(f"    [{categoria} / '{match.group()}'] ...{texto_orig[inicio:fim]}...")
    print()
