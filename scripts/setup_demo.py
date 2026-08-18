"""
Setup Demo - verifica se o ambiente esta pronto para rodar o dashboard.
Fase 15.6. Nao instala nada sozinho -- so diagnostica e orienta.

Uso: python scripts/setup_demo.py
"""
import sys
from pathlib import Path

def achar_raiz_projeto(caminho_inicial: Path) -> Path:
    atual = caminho_inicial.resolve()
    for pai in [atual] + list(atual.parents):
        if (pai / ".git").exists():
            return pai
    raise RuntimeError("Nao encontrei a raiz do projeto")

RAIZ = achar_raiz_projeto(Path(__file__))
sys.path.insert(0, str(RAIZ))

def checar_pacotes():
    pacotes = ["pandas", "numpy", "pyarrow", "streamlit", "altair", "lightgbm", "xgboost", "catboost", "sklearn"]
    faltando = []
    for pacote in pacotes:
        try:
            __import__(pacote)
        except ImportError:
            faltando.append(pacote)
    return faltando


def checar_artefatos():
    from src.analytics.dashboard_data import ARTIFACT_FILES
    base = RAIZ / "data" / "model_validation"
    faltando = []
    for chave, nome_arquivo in ARTIFACT_FILES.items():
        caminho = base / nome_arquivo
        if not caminho.exists():
            faltando.append(str(caminho.relative_to(RAIZ)))
    return faltando


def main():
    print("=" * 60)
    print("Procurement Intelligence Platform - Setup Demo")
    print("=" * 60)
    print()

    tudo_ok = True

    print("[1/2] Verificando pacotes Python...")
    faltando_pacotes = checar_pacotes()
    if faltando_pacotes:
        tudo_ok = False
        print(f"  FALTANDO: {', '.join(faltando_pacotes)}")
        print("  Rode: pip install -r requirements.txt")
    else:
        print("  OK - todos os pacotes necessarios estao instalados")
    print()

    print("[2/2] Verificando artefatos de dados (data/model_validation/)...")
    try:
        faltando_artefatos = checar_artefatos()
    except Exception as e:
        tudo_ok = False
        faltando_artefatos = None
        print(f"  ERRO ao verificar: {e}")

    if faltando_artefatos:
        tudo_ok = False
        print(f"  FALTANDO {len(faltando_artefatos)} arquivo(s):")
        for f in faltando_artefatos:
            print(f"    - {f}")
        print()
        print("  Esses artefatos sao gerados pelo pipeline oficial (scripts/pipeline/).")
        print("  Se voce clonou o repositorio do GitHub, eles ja deveriam estar la")
        print("  (versionados na Fase 15.3) -- verifique se o clone/pull esta completo.")
    elif faltando_artefatos is not None:
        print("  OK - todos os artefatos necessarios estao presentes")
    print()

    print("=" * 60)
    if tudo_ok:
        print("Ambiente pronto. Para abrir o dashboard:")
        print("  streamlit run app/dashboard.py")
    else:
        print("Ambiente incompleto -- resolva os itens acima antes de rodar o dashboard.")
    print("=" * 60)

    sys.exit(0 if tudo_ok else 1)


if __name__ == "__main__":
    main()
