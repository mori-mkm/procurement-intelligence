# Procurement Intelligence Platform

**[Acessar o dashboard ao vivo](https://procurement-intelligence-mkm.streamlit.app/)**

Plataforma de Spend and Price Intelligence construida sobre dados publicos
de compras do PNCP (compras.gov.br), usados como PROXY para procurement
corporativo. Projeto de portfolio para demonstrar competencia combinada
de Data Engineering e Data Science, direcionado a uma vaga hibrida de
Compras/Procurement em instituicao financeira.

LIMITACAO CENTRAL, valida para todo o projeto: os dados sao de compras
publicas, nao de procurement bancario real. A metodologia (pipeline,
benchmarking de preco, deteccao de anomalia, savings engine) e portatil
para sistemas corporativos como SAP Ariba, Coupa, Oracle Procurement.
Testamos filtrar por instituicoes financeiras publicas (Banco do Brasil,
Caixa) -- sem volume rastreavel no PNCP apesar de habilitacao formal
desde 2023. A alternativa adotada foi curar um subconjunto de categorias
de compra que se assemelham a procurement corporativo via palavra-chave
(ver ADR-0009).

## O problema de negocio

Onde estao as oportunidades de economia dentro das compras, e quais
transacoes apresentam preco significativamente acima do valor esperado?

## Arquitetura

Compras.gov.br / PNCP (bulk diario + anual)
    -> BRONZE  (dado bruto, tipagem defensiva de ID, deteccao de schema drift)
    -> SILVER  (dedup exata, resolucao de revisao temporal, categorizacao
                de relevancia, flag de resultado conflitante)
    -> GOLD    (dim_buyer, dim_item, dim_supplier, dim_date, fact_purchase
                -- grao: purchase_item_id x supplier_key)
        -> Spend Analytics   (spend por categoria, HHI, Curva ABC)
        -> Price Baseline    (mediana por item_key, split temporal)
        -> Price ML          (LightGBM, mesmas features + quantidade)
        -> Anomaly Detection (percentil de residuo do modelo)
        -> Savings Engine    (Potential Savings Opportunity)
        -> Dashboard         (Streamlit, arquitetura multipage)

O dashboard (app/dashboard.py) e um roteador enxuto que carrega
app/helpers.py (funcoes compartilhadas) e app/pages/ (uma pagina por
modulo de negocio). O deploy publico consome exclusivamente artefatos
compactos e versionados em data/model_validation/ -- nao depende do
Gold completo (5,8M linhas, nao versionado por exceder limites do
GitHub), garantindo que o app funcione de forma identica local e em
producao.

## Stack

Python 3.11, DuckDB (ingestao anual em streaming), pandas, LightGBM,
Streamlit, pytest (124 testes). Sem Spark/Airflow/Docker/cloud fixo --
decisao deliberada de escopo (ver fase0_design_procurement_intelligence.md).

## Escala dos dados processados

- Cobertura: 2022-2026 (enfase 2024-2026 no fato, conforme split temporal)
- 5.788.938 transacoes homologadas no fact_purchase
- 366.368 itens distintos, 192.266 fornecedores, 915.866 compradores
- Pipeline completo (Bronze a Gold, 3 anos): ~6-7 minutos

## Principais decisoes de arquitetura (ver docs/adr/ para o historico completo)

| Decisao | Resumo | ADR |
|---|---|---|
| CATMAT nao e chave confiavel de item | 52-81% de nulos medidos em dado real; item_key usa descricao normalizada | 0006 |
| Grao de fact_purchase | (purchase_item_id, supplier_key), ~0,08% de residuo aceito e documentado | 0004, 0013 |
| Arquivos anuais via DuckDB, nao diarios | Arquivos diarios tem gaps intermitentes imprevisiveis | 0007, 0011 |
| Split temporal (nunca random) | Treino=2024, Validacao=2025, Teste=2026 -- evita vazamento temporal | 0003 |
| Deteccao de outlier de valor | Duas camadas (z-score modificado + mediana global) -- reduziu spend inflado por erro de lancamento | 0014 |
| Escopo do baseline de preco | So item_key com >=5 transacoes no treino; agrupamento amplo testado e descartado | 0015 |

## Resultados (Modulo 1 -- Spend Intelligence)

- 8 categorias curadas de relevancia corporativa (TI, Consultoria,
  Facilities, Seguranca, Marketing, Telecom, Mobiliario, Locacao de
  Veiculos) capturam ~2,3-2,6% do volume total de transacoes do PNCP --
  o resto e compra publica sem paralelo corporativo (merenda, insumo
  hospitalar, obras).
- HHI calculado por categoria (nao agregado) apos remocao de outlier:
  todas as categorias na faixa nao concentrado a moderadamente
  concentrado -- mercado nacional pulverizado, sem monopolio real.
- Curva ABC de fornecedores disponivel por categoria via dashboard.

## Resultados (Modulo 2 -- Price Intelligence)

- Baseline (mediana por item_key): MAPE mediana ~78%, cobertura ~70-80%
  (so itens com volume minimo de treino).
- Modelo ML (LightGBM): MAPE mediana ~74-78% (empatado com o baseline --
  SHAP mostra que item_key domina a predicao). Ganho real: cobertura de
  100%, incluindo itens raros que o baseline nao cobre.
- Anomalias: sinalizadas por percentil do residuo, excluindo itens nunca
  vistos no treino.
- Savings potencial: separado entre alta confianca e itens de ticket
  alto que exigem cautela adicional. Rotulo sempre "Potential Savings
  Opportunity" -- nunca "sobreprecco confirmado" (requer revisao humana).

## Limitacoes conhecidas (honestas, nao escondidas)

- Dado e proxy publico, nao procurement bancario real.
- ML nao supera o baseline em precisao neste dataset -- so em cobertura.
- Deteccao de outlier nao garante 100% de limpeza -- heuristica
  pragmatica, nao prova estatistica (ver ADR-0014).
- Tabelas do dashboard (st.dataframe) tem fundo dependente do tema do
  navegador -- graficos e demais elementos ja tem tema fixo aplicado.
- Deflacao por IPCA (real_unit_price) prevista na Fase 0, nao implementada.

## Como acessar

### Opcao 1 -- Dashboard publicado (recomendado para avaliacao rapida)

https://procurement-intelligence-mkm.streamlit.app/

Consome artefatos compactos ja versionados no repositorio -- nao requer
nenhuma instalacao.

### Opcao 2 -- Rodar localmente

Pre-requisitos: Python 3.11+, Git.

    git clone https://github.com/mori-mkm/procurement-intelligence.git
    cd procurement-intelligence
    pip install -r requirements.txt
    python scripts/setup_demo.py
    streamlit run app/dashboard.py

O comando setup_demo.py verifica se os pacotes e os artefatos de dados
necessarios estao presentes antes de abrir o dashboard. Os artefatos de
Model Validation (data/model_validation/) ja vem versionados no
repositorio -- nao e necessario rodar o pipeline completo (Bronze ate
Gold) so para visualizar o dashboard.

Para reproduzir o pipeline completo (ingestao, Bronze, Silver, Gold,
treino de modelo) ao inves de usar os artefatos ja versionados, e
necessario baixar os dados brutos do PNCP (nao versionados, centenas de
MB) -- ver scripts/pipeline/ para os scripts oficiais, na ordem:
ingestao -> Silver/Gold -> model selection -> tuning -> avaliacao OOT ->
anomaly/savings -> artefatos compactos do dashboard.

## Estrutura do repositorio

    src/
    |-- ingestion/       # download idempotente (diario + anual via DuckDB)
    |-- quality/         # validacao Bronze, tipagem defensiva, schema drift
    |-- transformation/  # Silver e Gold
    `-- analytics/       # Spend Analytics, Price Baseline, ML, Anomaly, Savings
    app/
    |-- dashboard.py     # roteador principal
    |-- helpers.py        # funcoes compartilhadas entre paginas
    `-- pages/            # uma pagina por modulo de negocio (nome interno: paginas/)
    scripts/
    |-- pipeline/         # pipeline oficial de producao (Bronze a artefatos do dashboard)
    `-- setup_demo.py     # verificacao de ambiente antes de rodar o dashboard
    tests/                # 124 testes (pytest)
    docs/adr/             # ADRs -- Architecture Decision Records
    archive/               # investigacoes historicas ja resolvidas (referencia)
    fase0_design_procurement_intelligence.md  # design original completo
