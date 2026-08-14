# ADR-0018 — Dashboard Consome Artefatos Analíticos Validados

## Status

Accepted

## Contexto

A primeira versão do dashboard Streamlit executava parte da lógica analítica durante a inicialização da aplicação.

Entre outras operações, o dashboard:

- preparava dados para modelagem;
- treinava o modelo LightGBM;
- calculava previsões e resíduos;
- recalculava o threshold de anomalias;
- reconstruía Potential Savings.

Após a conclusão da validação temporal, seleção de modelo, teste OOT 2026, calibração de anomalias e auditoria de Savings, essa arquitetura deixou de ser adequada.

O dashboard deve representar a camada de consumo e tomada de decisão, e não a camada de treinamento e validação.

## Decisão

O dashboard Streamlit passa a consumir somente artefatos analíticos previamente calculados e validados.

Foi criada a camada:

```text
src/analytics/dashboard_data.py