import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

sys.path.insert(0, str(achar_raiz_projeto(Path(__file__))))

from datetime import date
import pandas as pd
from src.ingestion.pncp_bulk import local_path_for
from src.quality.checks import load_bronze_csv
from src.transformation.silver import build_silver_transformation_report
from src.transformation.gold import build_dim_item, normalize_item_key

dias = [date(2025, 12, 1), date(2026, 5, 22)]
frames = []
for dia in dias:
    df_bronze = load_bronze_csv(local_path_for(dia))
    _, df_silver = build_silver_transformation_report(df_bronze)
    frames.append(df_silver)

df_fact = pd.concat(frames, ignore_index=True)
dim_item = build_dim_item(df_fact)

texto_com_espaco = "Assistência médica - Hospitalar / Domiciliar complementar de saúde / Convênio"
texto_sem_espaco = "Assistência médica - Hospitalar / Domiciliar complementar desaúde / Convênio"

chave_esperada = normalize_item_key(texto_com_espaco)
chave_typo_antiga = normalize_item_key(texto_sem_espaco)

print("Chave esperada apos correcao:", repr(chave_esperada))
print("Chave que a versao ANTIGA (com typo) geraria:", repr(chave_typo_antiga))
print("As duas chaves sao iguais agora?", chave_esperada == chave_typo_antiga)
print()

linha_exata = dim_item[dim_item["item_key"] == chave_esperada]
print(f"Linhas com item_key EXATAMENTE igual a chave esperada: {len(linha_exata)}")
print(linha_exata[["item_key", "n_transacoes"]].to_string(index=False))
