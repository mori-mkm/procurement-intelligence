# ADR-0016: Seleção e validação temporal do modelo de Price Intelligence

## Status

Aceito

## Contexto

O módulo de Price Intelligence precisa estimar o preço unitário esperado de uma
compra sem utilizar informação futura e sem assumir a priori que um algoritmo
específico é superior.

Foi definido o seguinte protocolo temporal:

- 2024: treinamento;
- 2025: validação, seleção de algoritmo e tuning;
- 2026: teste final out-of-time, mantido isolado até o congelamento da decisão.

A métrica primária de seleção é MAE no log do preço unitário (`mae_log`).
Como métricas secundárias são acompanhados RMSE log, MedAPE, WAPE, MAE e RMSE
em preço.

Também é monitorado separadamente o desempenho em:

- item_key conhecido no treino;
- item_key não observado no treino (cold start).

## Modelos avaliados

Foram comparados:

1. Median Baseline por item_key;
2. Ridge Regression com One-Hot Encoding;
3. LightGBM;
4. CatBoost;
5. XGBoost.

Os modelos supervisionados foram avaliados nas mesmas 57.452 transações da
validação de 2025.

O Median Baseline apresentou cobertura de 79,91%, portanto sua comparação com
os modelos foi realizada também em uma amostra comum de 45.912 observações.

## Resultados da validação 2025

### Modelos supervisionados

| Modelo | MAE log | RMSE log | MedAPE | WAPE |
|---|---:|---:|---:|---:|
| LightGBM | 1.214258 | 1.683503 | 73.84% | 94.41% |
| XGBoost | 1.224094 | 1.692444 | 74.66% | 94.37% |
| CatBoost | 1.254234 | 1.701370 | 77.46% | 95.65% |
| Ridge | 1.371005 | 1.820814 | 81.97% | 95.76% |

### Comparação same-sample com Median Baseline

Nas 45.912 observações cobertas pelo baseline:

| Modelo | MAE log |
|---|---:|
| LightGBM | 1.092360 |
| XGBoost | 1.110898 |
| CatBoost | 1.160534 |
| Ridge | 1.290365 |
| Median Baseline | 1.650563 |

O LightGBM reduziu o MAE log em aproximadamente 33,8% em relação ao Median
Baseline nessa mesma amostra.

## Bootstrap pareado por item_key

Foi utilizado clustered paired bootstrap com 5.000 reamostragens,
reamostrando `item_key` com reposição e preservando todas as transações
pertencentes ao cluster sorteado.

### LightGBM vs XGBoost

- delta MAE log (XGBoost - LightGBM): +0.009836;
- diferença relativa: +0,81%;
- IC95%: [-0.004563, +0.022731];
- conclusão: inconclusivo.

Não há evidência suficiente para afirmar superioridade estatística do
LightGBM sobre o XGBoost.

### LightGBM vs CatBoost

- delta: +0.039976;
- IC95%: [+0.017894, +0.061153];
- conclusão: LightGBM melhor.

### LightGBM vs Ridge

- delta: +0.156746;
- IC95%: [+0.098044, +0.210103];
- conclusão: LightGBM melhor.

### LightGBM vs Median Baseline

Na amostra comum:

- delta: +0.558204;
- IC95%: [+0.281591, +0.946670];
- conclusão: LightGBM melhor.

## Cold start

Na validação 2025:

- itens conhecidos: 83,78%;
- itens unseen: 16,22%.

MAE log:

- LightGBM known: 1.117448;
- LightGBM unseen: 1.714354;
- XGBoost known: 1.113673;
- XGBoost unseen: 1.794498.

Embora XGBoost tenha desempenho ligeiramente melhor nos itens conhecidos,
LightGBM apresentou menor erro global e melhor desempenho em cold start.

## Tuning do LightGBM

Foi realizado tuning controlado em duas etapas, utilizando exclusivamente 2025.

O melhor candidato encontrado foi:

- num_leaves = 63;
- min_child_samples = 10;
- learning_rate = 0.03;
- reg_alpha = 0;
- reg_lambda = 0;
- best_iteration = 288.

Resultado:

- LightGBM v0 MAE log: 1.214258;
- tuned MAE log: 1.211966;
- melhoria observada: 0,189%.

Bootstrap pareado v0 vs tuned:

- delta tuned - v0: -0.002293;
- IC95%: [-0.006059, +0.001178];
- conclusão: inconclusivo.

O ganho do tuning não foi considerado material ou estatisticamente consistente.

## Decisão

O modelo selecionado para o teste final é o **LightGBM v0**.

Parâmetros congelados:

- n_estimators = 300;
- learning_rate = 0.05;
- num_leaves = 63;
- min_child_samples = 10;
- random_state = 42.

A escolha considera:

1. menor MAE log observado entre os modelos supervisionados;
2. desempenho estatisticamente superior a CatBoost e Ridge;
3. ganho substancial sobre o baseline de negócio;
4. desempenho melhor que XGBoost em itens unseen;
5. ausência de ganho material comprovado com tuning adicional;
6. preferência por parcimônia quando a complexidade adicional não produz
   benefício consistente.

LightGBM e XGBoost são considerados estatisticamente equivalentes na validação
2025; não será alegada superioridade estatística do LightGBM sobre XGBoost.

## Protocolo para o teste final

Após esta decisão:

1. nenhuma seleção de algoritmo ou hiperparâmetro poderá utilizar 2026;
2. LightGBM v0 será retreinado utilizando 2024 + 2025;
3. categorias serão aprendidas exclusivamente no histórico 2024-2025;
4. categorias novas de 2026 serão tratadas como unseen/missing;
5. 2026 será avaliado uma única vez como teste out-of-time;
6. resultados ruins em 2026 serão documentados, não utilizados para retuning.

Serão avaliados no teste:

- MAE log;
- RMSE log;
- MedAPE;
- WAPE;
- MAE e RMSE em preço;
- known vs unseen;
- desempenho por categoria;
- estabilidade temporal.

## Consequências

A decisão reduz o risco de escolher um modelo com base em pequenas variações
da validação e preserva 2026 como teste independente.

Caso o desempenho em 2026 se deteriore, a deterioração será tratada como
evidência de drift ou perda de generalização, e não como justificativa para
ajustar retrospectivamente o modelo ao teste.