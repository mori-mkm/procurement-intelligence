# ADR-0017 — Calibração de Anomalias e Confidence Tiers de Savings

## Status

Accepted

## Contexto

O módulo de Price Intelligence identifica desvios entre o preço observado e o preço esperado pelo modelo.

A implementação inicial classificava anomalias utilizando um percentil calculado sobre o próprio conjunto analisado. Essa abordagem não era adequada para avaliação out-of-time, pois o threshold poderia variar utilizando informação do período de teste.

Além disso, o cálculo bruto de Potential Savings:

potential_saving = max(unit_price - expected_price, 0) * quantity

produzia valores elevados em registros que poderiam apresentar problemas de comparabilidade de unidade, pouco histórico ou tickets de alto valor.

Era necessário separar:

- detecção estatística de anomalias;
- priorização financeira;
- confiabilidade da oportunidade.

## Decisão

### 1. Threshold de anomalia

O threshold oficial de anomalia será calibrado exclusivamente no conjunto de validação de 2025.

A calibração utiliza:

- apenas itens conhecidos (`known`);
- percentil 95 do `abs_log_error`.

Threshold congelado:

```text
abs_log_error = 3.284766