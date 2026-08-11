# ADR-0005: Tratamento de heterogeneidade de unidade de medida

## Status
Aceito

## Contexto
A Fase 0 identificou como risco crítico a possibilidade de o mesmo item
aparecer com unidades de medida diferentes (unidade, caixa, litro etc.),
o que inviabilizaria comparação de preço sem tratamento. A Fase 1 mediu a
magnitude real, em amostra de 5.000 linhas:

- Por CATMAT (`cod_item_catalogo`), quando presente: **9,77%** dos códigos
  têm mais de 1 unidade de medida distinta.
- Por descrição resumida (fallback para os ~28% sem CATMAT): **14,93%**.
- Um pequeno subconjunto de códigos concentra o problema — alguns chegam a
  5-6 unidades distintas para o mesmo código.

## Decisão
Tratar a heterogeneidade de unidade como regra de exceção no Silver, não
como redesenho geral:

1. Para a maioria dos itens (unidade única), seguir sem alteração.
2. Para o subconjunto com múltiplas unidades, aplicar uma tabela de
   conversão curada manualmente onde houver fator de conversão claro e
   verificável (ex: caixa → unidade, com multiplicador conhecido).
3. Onde não houver fator de conversão confiável, excluir essa combinação
   (item, unidade) do benchmarking direto de preço, marcando
   explicitamente como "não comparável" — não comparar preços de unidades
   diferentes silenciosamente.

## Consequências
- Exige construir e manter uma tabela de conversão pequena, com curadoria
  manual — esforço recorrente, não automatizado no MVP.
- Um subconjunto de compras ficará fora da cobertura do Price Intelligence.
  Isso deve ser acompanhado como Model KPI de cobertura (% das compras que
  o modelo consegue precificar), já previsto na Fase 0.
- README deve deixar claro que essa exclusão é uma escolha metodológica
  consciente, não uma lacuna não percebida.

## Alternativas consideradas
- **Descartar qualquer item com mais de uma unidade observada:** rejeitada
  — agressiva demais, jogaria fora ~85-90% de dado comparável legítimo
  junto com a minoria problemática.
- **Conversão automática via NLP/regex sobre o texto da unidade, sem
  curadoria manual:** rejeitada para o MVP — risco maior de erro silencioso;
  fica como candidato a V2 quando o volume justificar o investimento.
