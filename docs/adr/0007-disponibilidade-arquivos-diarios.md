# ADR-0007: Arquivo diário como fonte não confiável para backfill histórico

## Status
Aceito

## Contexto
Testamos a disponibilidade do endpoint `diario/` do repositório bulk em 9
datas espalhadas entre dez/2025 e jul/2026:

| Data | Disponível? |
|---|---|
| 01/dez/2025 | ✅ |
| 22/jan/2026 | ✅ |
| 15/abr/2026 | ✅ |
| 01/mai/2026 | ❌ |
| 15/mai/2026 | ❌ |
| 22/mai/2026 | ✅ |
| 29/mai/2026 | ❌ |
| 02/jun/2026 | ❌ |
| 01/jul/2026 | ❌ |

O padrão não segue um corte temporal limpo (não é "parou de publicar depois
de X"), nem se explica por dia da semana ou feriado de forma consistente —
22/mai funcionou cercado de 404 dos dois lados, na mesma sexta-feira que
outras sextas falharam. É um gap intermitente e não-sistemático na
publicação da pasta `diario/`, não uma janela de retenção nem uma
interrupção definitiva.

Em contraste, a Fase 1 já validou que os arquivos `anual/` respondem de
forma consistente para todos os anos de 2021 a 2026 (contagem via DuckDB,
sem falha em nenhum ano).

## Decisão
Tratar `diario/` como fonte oportunista de atualização incremental, não
como fonte confiável de backfill histórico. Para a ingestão histórica
2024-2026 (janela definida no ADR-0003), usar os arquivos `anual/` como
fonte de verdade. `diario/` fica reservado para uma futura camada de
atualização incremental, com 404 tratado como situação esperada e
recorrente — não como erro excepcional que deveria travar o pipeline.

## Consequências
- `pncp_bulk.py` hoje só sabe baixar `diario/` — vai precisar de uma nova
  função para `anual/`, com estratégia de download diferente: os arquivos
  anuais são ordens de grandeza maiores (potencialmente GB), então
  `resp.content` direto na memória não escala; precisa de streaming em
  chunks.
- `count_lines()` (leitura linha a linha em Python puro) não escala para
  arquivo de GB — para os anuais, a contagem deve usar DuckDB (mesma
  abordagem já validada na Fase 1), não a implementação atual.
- Idempotência para arquivo de GB pede mais cautela: um re-download forçado
  tem custo de tempo/banda bem maior do que no caso diário.

## Alternativas consideradas
- **Manter `diario/` como fonte primária e preencher gaps manualmente:**
  rejeitada — não escala, e não há garantia de que os gaps sejam
  percebidos automaticamente sem uma checagem sistemática.
- **Usar a API paginada para preencher os dias faltantes:** rejeitada — a
  Fase 1 já confirmou que o endpoint de itens via API
  (`2_consultarItensContratacoes_PNCP_14133`) retorna 404 de forma
  consistente, não é um fallback confiável.
