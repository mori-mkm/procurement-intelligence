# ADR-0011: Uso de arquivos anuais via DuckDB para cobertura de dim_buyer

## Status
Aceito

## Contexto
A primeira versão de dim_buyer (Fase 4) usou o arquivo diário de cabeçalho
(VW_FT_PNCP_COMPRA) do mesmo dia do item. O join resultante teve 42-45% de
linhas sem UF/modalidade — investigação confirmou a causa: o item de um dia
referencia id_compra publicados meses ou anos antes (mediana das linhas sem
match: 17/out/2025, contra 01/dez/2025 nas linhas com match; mínimo
observado: 2023-10-17). Item e cabeçalho do mesmo dia não são snapshots do
mesmo universo temporal.

Backfill diário incremental não resolveria — a cauda de datas se espalha
por mais de 2 anos, exigiria ingerir cabeçalho de praticamente todo dia
desde 2023. Optou-se por materializar arquivos anuais completos de
cabeçalho (mesmo padrão já usado para contagem de item na Fase 1 e busca
BB/Caixa, ADR-0007/0009), cobrindo a janela do split temporal do ADR-0003
(2024, 2025, 2026).

Ao combinar os 3 anos, surgiu id_compra duplicado (4.782 de 771.720, 0,62%)
— dois fenômenos distintos: (1) duplicata dentro do mesmo arquivo anual
(1.720 casos, concentrados em 2024, causa não identificada com certeza —
data_atualizacao_pncp nula nos casos observados, sem sinal de qual versão é
válida); (2) sobreposição entre arquivos anuais adjacentes (3.073 IDs,
compra publicada perto da virada do ano aparecendo nos dois snapshots).

## Decisão
1. `src/ingestion/pncp_bulk_annual.py`: novo módulo, usa DuckDB
   (`read_csv_auto` com streaming + `COPY ... TO ... FORMAT PARQUET`) em vez
   de `requests.get()` — arquivos anuais são grandes demais para memória
   Python direta. Campos de ID forçados a VARCHAR **na leitura** (não depois
   — zero à esquerda já é perdido se o DuckDB inferir tipo primeiro).
2. Materializa como Parquet local, não mantém CSV cru — mais compacto e
   rápido de reconsultar.
3. `resolve_duplicate_buyer_records`: mantém a linha com `data_publicacao_pncp`
   mais recente por `id_compra`. Critério imperfeito (não temos
   `data_atualizacao_pncp` populada nos casos de duplicata interna para um
   desempate mais preciso), mas é o único campo disponível e consistente.

Resultado: `pct_sem_match` caiu de 44,75%/42,13% para 0,02%/0,05% nos dois
dias de referência.

## Consequências
- Nova dependência: `pyarrow` (engine Parquet do pandas).
- Materialização anual é mais lenta que diária (30-45s por ano nos testes,
  vs. segundos para diário) — aceitável por ser operação pontual, não
  recorrente a cada execução do pipeline.
- Cauda anterior a 2024 (compras publicadas em 2023, ainda aparecendo em
  resultados homologados posteriormente) permanece sem cabeçalho — aceito
  como limitação, já que 2023 está fora da janela de treino do ADR-0003.
- Causa raiz da duplicata dentro do mesmo ano (fenômeno 1) não foi
  totalmente esclarecida — fica como investigação futura se o padrão se
  mostrar relevante em volume maior.

## Alternativas consideradas
- **Backfill diário de cabeçalho para todas as datas referenciadas**:
  rejeitada — escala equivalente a ingerir ~2 anos de arquivos diários,
  sem vantagem sobre baixar o anual direto.
- **Aceitar cobertura parcial (42-45% sem match) como limitação do MVP**:
  rejeitada — UF e modalidade são atributos centrais do Módulo 1 (Spend por
  região), perda de quase metade do volume inviabilizaria essa análise.