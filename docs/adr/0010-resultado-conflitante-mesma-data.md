# ADR-0010: Tratamento de resultados conflitantes na mesma data

## Status
Aceito

## Contexto
Fase 3 identificou 21 grupos (42 linhas, 0,19% do dia 22/05/2026) da chave
composta (id_compra_item x cod_fornecedor) com mesma data_resultado mas
valor_unitario_resultado divergente -- todos concentrados em uma unica
compra (RIO NEGRO INDUSTRIA DE ALIMENTOS). Investigacao de campos adicionais
(data_atualizacao_pncp com granularidade de segundo, situacao_compra_item)
nao revelou nenhum criterio de desempate: os 21 pares tem timestamps de
atualizacao identicos ou dentro de uma janela de ~3 segundos, e ambas as
linhas de cada par estao marcadas "Homologado". Padrao consistente com um
evento de reprocessamento em lote na fonte (PNCP/sistema de origem), nao
com erro de digitacao ou revisao legitima ao longo do tempo (ADR-0004 ja
resolve esse segundo caso via resolve_temporal_revisions).

## Decisao
Adicionar flag nao-destrutiva `resultado_conflitante` (mesmo padrao de
`unit_flag`, ADR-0005/0006). Comportamento por consumidor, nao uma regra
unica:

- **Spend Analytics**: excluir linhas conflitantes da soma
  (compute_spend_total) -- somar as duas infla o gasto ~2x nesses casos.
- **Price Benchmarking**: manter todas as linhas -- um segundo ponto de
  preco observado para o mesmo item nao prejudica analise de dispersao,
  mesmo vindo de reprocessamento.

## Consequencias
- Spend Analytics tera "spend_total_bruto" e
  "spend_total_liquido_sem_conflitos" reportados separadamente -- README
  deve deixar claro qual numero usar em qual contexto.
- Acompanhar pct_linhas_flagadas como Data Quality KPI (previsto na Fase 0)
  -- pequeno agora (0,19%) mas pode crescer com mais dias/volume.
- Nao investigamos se esse padrao de reprocessamento em lote e recorrente
  em outras compras/dias -- fica como hipotese a confirmar se o percentual
  subir significativamente em volume maior.

## Alternativas consideradas
- **Excluir de ambos os usos**: rejeitada -- desperdica dado utilizavel no
  Price Benchmarking, onde o conflito nao atrapalha.
- **Escolher automaticamente um dos dois valores (ex: menor)**: rejeitada
  -- nao ha evidencia de qual valor esta correto; seria inventar resposta.