# ADR-0012: fact_purchase contém apenas transações com resultado homologado

## Status
Aceito

## Contexto
~57% do Silver combinado (28.918 de 50.703 linhas, Fase 4) são itens ainda
em andamento (tem_resultado=False) -- sem fornecedor, preço, quantidade ou
data de resultado definidos. Mantê-los em fact_purchase deixaria mais da
metade da tabela com todas as métricas de negócio nulas.

## Decisão
build_fact_purchase filtra por valor_unitario_resultado not-null antes de
montar o fato. Itens em andamento permanecem no Silver (nenhum dado é
perdido na camada intermediária), apenas não entram no fato de consumo
analítico. Estatística de exclusão (n_excluidos_sem_resultado_homologado)
é reportada explicitamente, não descartada silenciosamente.

## Consequências
- fact_purchase representa só transações realizadas -- alinhado à
  convenção usual de modelo dimensional (fato = evento de negócio
  concretizado).
- Quem precisar analisar "pipeline de compras em andamento" (não é o caso
  do MVP atual) precisará consultar o Silver diretamente, não o Gold.
- Spend total calculado sobre fact_purchase já filtrado é o "gasto
  realizado", não o "gasto orçado/estimado total" -- distinção a deixar
  clara no README.