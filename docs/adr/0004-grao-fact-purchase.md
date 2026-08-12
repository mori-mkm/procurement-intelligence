# ADR-0004: Grão da fact_purchase — chave composta e deduplicação prévia

## Status
Aceito

## Contexto
A Fase 0 assumiu grão = item de compra (id_compra_item). A Fase 1 mediu, em
amostra real do CSV bulk, que 3,38% dos id_compra_item aparecem duplicados.
Inspeção manual da amostra de duplicados revelou dois fenômenos distintos
misturados no mesmo número:

1. **Múltiplos fornecedores homologados legitimamente** para o mesmo item
   (ex: Sistema de Registro de Preços com mais de um vencedor) — mesmo
   id_compra_item, cod_fornecedor diferente, valores diferentes.
2. **Linhas duplicadas de fato** — mesmo id_compra_item, mesmo
   cod_fornecedor, mesmo valor_unitario_resultado, mesma
   quantidade_resultado. Isso parece um artefato de ingestão/exportação do
   arquivo bulk, não um caso de negócio legítimo.

O percentual real de multiplicidade legítima (caso 1) é, portanto, menor que
3,38% — o número medido mistura os dois fenômenos.

## Decisão
1. Adicionar uma etapa de deduplicação no Silver que remove linhas
   exatamente idênticas em todas as colunas antes de qualquer análise de
   grão ou carga no Gold.
2. Após a deduplicação, definir o grão da fact_purchase como chave composta
   **(id_compra_item × cod_fornecedor)**, não id_compra_item isolado.
3. Re-medir a taxa real de multiplicidade 1:N depois da deduplicação, para
   dimensionar corretamente o impacto no modelo dimensional.

## Consequências
- Adiciona uma etapa explícita de deduplicação exata no pipeline Silver,
  antes da etapa de carga do Gold.
- Spend Analytics que precisa de total por item (não por item×fornecedor)
  deve agregar explicitamente somando entre fornecedores — documentar essa
  regra na camada de Analytics, não deixar implícito.
- Para benchmarking de preço, tratar cada linha item×fornecedor como uma
  observação distinta é desejável (mais variância observada = benchmark mais
  robusto), mas isso precisa ser uma decisão explícita e documentada, não
  um efeito colateral acidental do grão escolhido.

## Alternativas consideradas
- **Manter id_compra_item como grão único, descartando duplicatas mantendo
  a primeira linha:** rejeitada — descarta silenciosamente fornecedores
  legítimos junto com as duplicatas espúrias, sem diferenciar os dois casos.
- **Colapsar sempre em uma linha por item (ex: usando o menor preço
  homologado):** rejeitada — perde o sinal de dispersão de preço entre
  fornecedores, que é justamente o que o Módulo de Price Intelligence
  precisa capturar.

## Nota adicional: cod_fornecedor pode ser CPF, não só CNPJ (Fase 4)

fact_purchase revelou casos onde cod_fornecedor tem 11 dígitos (formato
CPF, pessoa física) em vez de 14 (CNPJ, pessoa jurídica) -- observado em
contratos de fornecimento de água por carro-pipa (PI), plausivelmente
Sistema de Registro de Preços com múltiplos fornecedores pessoa física
cadastrados ao mesmo preço-teto. Relevante para qualquer enriquecimento
futuro via Receita Federal (que cobre CNPJ, não CPF) -- dim_supplier
precisará tratar os dois formatos distintamente quando essa fase chegar.
