# ADR-0003: Split temporal de treino/validação/teste revisado

## Status
Aceito

## Contexto
A Fase 0 assumiu treino em 2022-2024, validação em 2025, teste em 2026,
partindo do princípio de que o volume de dados seria razoavelmente estável
ano a ano. A Fase 1 (Data Discovery) mediu o volume real de registros por
ano na base VW_FT_PNCP_COMPRA_ITEM:

| Ano | Registros |
|---|---:|
| 2021 | 28.892 |
| 2022 | 156.285 |
| 2023 | 290.640 |
| 2024 | 1.642.583 |
| 2025 | 4.736.611 |
| 2026 (parcial) | 3.268.675 |

Essa curva reflete a adoção gradual e obrigatória da Lei 14.133/2021 pelos
órgãos públicos, não uma variação orgânica de volume de compras. 2022 e 2023
não representam o universo completo de compras públicas — só os órgãos que
já haviam migrado do regime antigo (Lei 8.666) para o novo.

## Decisão
Revisar o split temporal para:

- **Treino:** 2024
- **Validação:** 2025
- **Teste:** 2026 (parcial, até a data de corte do projeto)

2021-2023 são excluídos do treino por não representarem de forma confiável
o comportamento de preços do universo de compras públicas no período.

## Consequências
- Janela de treino menor que o planejado originalmente (1 ano em vez de 3),
  o que aumenta o risco de o modelo não capturar bem sazonalidade
  (ex: padrões de fim de ano fiscal).
- Se o modelo underperformar por falta de dado, 2023 pode ser reincorporado
  como treino suplementar, com ponderação menor e essa limitação documentada
  explicitamente — não como decisão padrão, só como fallback caso necessário.
- Essa limitação precisa aparecer no README do projeto, não só neste ADR.

## Alternativas consideradas
- **Manter 2022-2024 como treino (proposta original):** rejeitada — inclui
  anos com volume não-representativo, o que pode enviesar o baseline de
  preço mediano por CATMAT/período nesses anos.
- **Usar 2021-2025 inteiro como treino, só 2026 como teste:** rejeitada —
  dilui os padrões de preço mais recentes com anos historicamente
  incompletos, e não deixa janela separada para validação/tuning.
