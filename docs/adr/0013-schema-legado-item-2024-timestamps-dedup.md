# ADR-0013: Schema legado em arquivos anuais de item (2024) e timestamps de metadado no dedup

## Status
Aceito

## Contexto
Ao combinar arquivos anuais de item (2024+2025+2026) pela primeira vez,
o grão da fact_purchase quebrou: 211.416 grupos duplicados nao flagados
(3,68% do total). Investigacao revelou duas causas combinadas:

1. Arquivos anuais de 2024 usam nomes de coluna diferentes de 2025+:
   descricao/descricao_resumida, data_inclusao/data_inclusao_pncp,
   data_atualizacao/data_atualizacao_pncp (entre outras nao usadas pelo
   pipeline). select_necessary_columns descartava essas colunas
   silenciosamente para 2024, deixando ~1,64M linhas com item_key=None
   apos concat -- inuteis para dim_item/categorizacao/unit_flag.

2. Mesmo corrigindo (1), o mesmo item/fornecedor pode aparecer em anos
   anuais adjacentes com valores de negocio identicos (preco, quantidade,
   data_resultado) mas data_atualizacao_pncp diferente -- a fonte
   re-captura o registro a cada snapshot anual, sem mudanca de negocio.

## Decisao
1. normalize_legacy_column_names (checks.py), chamada dentro de
   select_necessary_columns: renomeia coluna legada para o nome canonico
   apenas quando o canonico esta ausente -- nunca sobrescreve dado real.
2. data_atualizacao_pncp e data_inclusao_pncp adicionados a
   COLUNAS_IGNORAR_NA_DEDUP: sao metadados de quando o sistema de origem
   tocou no registro, nao fatos de negocio observados (data_resultado
   continua sendo o fato de negocio relevante, ja usado em
   resolve_temporal_revisions).

## Consequencias
- Pipeline precisa ser re-executado do zero para 2024+2025+2026 -- o Gold
  ja persistido antes desta correcao esta com item_key=None para todo 2024
  e nao deve ser usado.
- Alias de coluna legada e especifico para 2024; se anos anteriores
  (2022/2023) forem usados como item no futuro, verificar se tem o mesmo
  padrao antes de assumir.
- Nao investigamos se ha outras colunas com nome legado alem das 3
  mapeadas -- as 3 sao as unicas usadas por NECESSARY_COLUMNS; outras
  diferencas de nome (numero_item, item_categoria_id,
  criterio_julgamento_id) nao afetam o pipeline atual.

## Alternativas consideradas
- **Ignorar 2024 inteiro, processar so 2025-2026:** rejeitada -- perde
  1,64M linhas de dado valido por um problema de nomenclatura corrigivel.
- **Adicionar somente ao dedup (sem corrigir nomes de coluna):** rejeitada
  -- nao resolve o problema maior (item_key=None para 2024), que afeta
  dim_item/categorizacao independente do dedup.

## Atualizacao: correcao de valor estimado no dedup (segunda rodada, mesma investigacao)

Apos a correcao de aliases/timestamps, 147.615 grupos ainda violavam o
grao. Quantificacao completa (nao amostra) revelou:
- 99,77% (147.274): valor_unitario_resultado/valor_total_resultado
  IDENTICOS entre as linhas -- so valor_unitario_estimado/valor_total
  (estimativa pre-licitacao) diferiam. A fonte re-edita a estimativa entre
  snapshots anuais sem o resultado homologado mudar.
- 0,22% (327): orgao_entidade_cnpj DIFERENTE entre as linhas -- colisao
  real de id_compra_item entre orgaos distintos. Volume pequeno demais
  para justificar mudar o grao para incluir orgao_entidade_cnpj (custo de
  complexidade na arquitetura inteira); aceito como limitacao conhecida.
  Consequencia: nesses ~327 casos, resolve_temporal_revisions ou
  flag_conflicting_results podem ter tratado compras de orgaos diferentes
  como se fossem revisao do mesmo registro -- erro pre-existente,
  nao amplificado por esta correcao.
- 0,01% (14): sem causa identificada, volume irrelevante para investigar.

Decisao: valor_unitario_estimado e valor_total adicionados a
COLUNAS_IGNORAR_NA_DEDUP.

## Encerramento da investigacao (terceira e ultima rodada)

Apos as tres correcoes desta investigacao (aliases de coluna legada 2024;
timestamps de metadado + valor estimado; nome_fornecedor + quantidade
estimada), o residuo final de violacoes de grao nao flagadas caiu para
4.812 de 5.788.938 linhas no fact_purchase combinado (2022-2026): **0,083%**.

Composicao estimada do residuo, por amostragem nas rodadas anteriores:
- Maioria: colisao real de id_compra_item entre orgaos distintos (~0,22%
  medido antes da ultima correcao) -- aceito como limitacao conhecida,
  volume pequeno demais para justificar mudar o grao para uma tripla
  (id_compra_item x cod_fornecedor x orgao_entidade_cnpj).
- Resto: descricao_resumida e outras colunas de baixa frequencia (<2% cada
  na amostra), nao perseguidas individualmente -- risco de over-merge
  (tratar itens genuinamente diferentes como duplicata) supera o beneficio
  de fechar um residuo ja pequeno.

Decisao de parada: criterio definido a priori (abaixo de 0,5% do
fact_purchase) foi atingido. Nao investigar mais essa classe de problema
neste momento -- revisitar apenas se o percentual crescer de forma visivel
com mais anos/volume de dado no futuro.