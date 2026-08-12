# ADR-0006: Estratégia de chave de item diante de alta taxa de null em CATMAT

## Status
Aceito

## Contexto
A Fase 1 estimou 27,98% de null em CATMAT (`cod_item_catalogo`), a partir de
uma amostra viesada — as primeiras 5.000 linhas do CSV bulk, não uma amostra
aleatória. A Fase 2 mediu o campo em arquivos diários completos, em 4 dias
reais espalhados ao longo de ~5 meses (dez/2025 a mai/2026):

| Data | CATMAT ausente |
|---|---|
| 01/dez/2025 | 52,42% |
| 22/jan/2026 | 63,34% |
| 15/abr/2026 | 62,04% |
| 22/mai/2026 | 81,32% |

O campo está ausente na **maioria** dos registros em todos os dias medidos,
variando entre ~52% e ~81% — sem convergir para um número único. A estimativa
original da Fase 1 subestimou a taxa real de null por causa do viés de
amostragem, não porque o dado mudou ao longo do tempo.

## Decisão
Usar `descricao_resumida` normalizada (lowercase, remoção de acentuação e
pontuação, trimming) como **chave primária** de agrupamento de item para
benchmarking de preço. `cod_item_catalogo` passa a ser um campo de
**enriquecimento**, usado quando presente para cruzar com o catálogo oficial
de materiais/serviços, mas não é mais premissa de que o pipeline core
depende.

Reportar a taxa de null como faixa observada (~52-81%), não como número
único de falsa precisão — a variação dia a dia é grande demais para um
ponto só representar o comportamento real da fonte.

## Consequências
- Normalização de texto livre é trabalho real e recorrente no Silver — vai
  precisar de manutenção contínua conforme surgirem variações de escrita
  não previstas (abreviações, ordem de palavras, erros de digitação).
- Cobertura do modelo de preço será menor que 100% das transações mesmo com
  o fallback de descrição — texto livre também tem ruído. Isso já era
  esperado desde a Fase 0 como Model KPI de cobertura, mas o número real
  provavelmente será mais conservador do que se assumíssemos CATMAT
  confiável.
- Fica em aberto se `codigo_NCM` (Nomenclatura Comum do Mercosul, também
  presente no schema) pode servir de chave alternativa ou complementar —
  não testamos sua completude ainda. Não assumir sem medir; investigar em
  fase futura se a normalização de descrição não for suficiente sozinha.

## Alternativas consideradas
- **Manter CATMAT como chave única:** rejeitada — descartaria mais de
  metade do spend do benchmarking de preço em qualquer dia medido.
- **Fixar um número único de taxa de null (ex: "~64%, média dos 4 dias") no
  lugar de uma faixa:** rejeitada — a variação real (52-81%) é grande
  demais para um ponto médio representar o comportamento da fonte sem
  enganar quem ler a documentação depois.

## Nota adicional: fragmentação de item_key por erro tipográfico na fonte (Fase 4)

Identificamos que erros de digitação na fonte (palavras coladas, ex:
"complementar desaude" vs "complementar de saude") fragmentam o que deveria
ser o mesmo item em duas entradas de item_key. Caso confirmado: 630
transações combinadas, contadas como 2 itens antes da correção.

Decisão: lista curada de correções pontuais (CORRECOES_TIPOGRAFICAS_CONHECIDAS,
em src/transformation/gold.py), aplicada apenas à construção de item_key,
nunca ao campo descricao_resumida observado. Cada entrada exige confirmação
manual em dado real -- rejeitamos fuzzy-match/similaridade automática por
risco de fundir itens genuinamente diferentes (ex: variações de tamanho,
modelo). Lista deve crescer incrementalmente conforme novos casos forem
identificados, não de uma vez por suposição.