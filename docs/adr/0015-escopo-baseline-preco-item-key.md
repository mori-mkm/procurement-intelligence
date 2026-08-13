# ADR-0015: Escopo do baseline de preço — item_key com volume mínimo, sem agrupamento amplo

## Status
Aceito

## Contexto
Cauda longa de item_key: 84% dos itens (14.793 de 17.539, no universo de
categorias relevantes) têm menos de 5 transações, mas representam só
~9% do spend relevante — mediana de 1 transação por item, insuficiente
para qualquer estatística confiável.

Testamos agrupamento por família curada (2+ palavras-âncora, mesmo padrão
do ADR-0009) como alternativa para dar volume a esses itens raros:
- `suprimento_impressora` (cartucho+impressora, toner, tinta+impressora):
  2.155 itens, mas mediana de preço variando de R$12,84 a R$4.552,29 (350x)
  -- mistura justificável por natureza real do produto (cartucho colorido
  pequeno vs. toner industrial), mas inválida para baseline de preço sem
  sub-segmentação adicional.
- `licenciamento_software` (cessão+programas+computador): 1.406 itens,
  mas maioria com texto duplicado no item_key (mesmo bug do ADR-0010, não
  resolvido) inflando a contagem, e preço fundamentalmente incomparável
  (por usuário/mês, perpétuo, por módulo, por pacote de N licenças
  misturados sob o mesmo agrupamento).

## Decisão
Baseline de preço (Fase 7) usa exclusivamente item_key com
min_transacoes >= 5 (865 itens, 90,1% do spend relevante). Itens abaixo
do threshold recebem baseline_confiavel=False, não são descartados do
dataset, apenas não têm preço esperado calculado.

item_family (se implementada) fica reservada para agregação de
Spend Analytics (Fase 6) -- "quanto se gasta com suprimento de
impressão no total" é pergunta valida para agrupamento amplo; "qual o
preço esperado deste item" não é, dado o teste acima.

## Gatilho para revisitar
Se, ao treinar o modelo de preço (Fase 8), o volume de item_key com
baseline confiavel (865 itens) se mostrar insuficiente para um dataset de
treino com poder preditivo minimo -- reavaliar agrupamento da cauda longa
com metodo mais robusto que palavra-chave manual: candidatos a testar
nesse momento, não antes: (1) sub-segmentação dentro de familia ampla por
atributo estruturado do texto (marca, capacidade, cor -- já presentes na
descrição, extraíveis por regex mais específico que o testado aqui);
(2) CATMAT como chave alternativa nos ~19-48% de itens que o têm
preenchido (ADR-0006), mesmo não sendo confiável como chave única;
(3) fuzzy matching/embeddings com validação manual de amostra antes de
aplicar em produção -- não aplicar sem revisão, dado o risco já
demonstrado de fusão incorreta.

## Alternativas consideradas
- **Agrupar por família ampla direto para baseline:** rejeitada com
  evidência de dado real (ver Contexto) -- preço não comparável dentro da
  família nas duas candidatas testadas.
- **Baixar o threshold de min_transacoes:** rejeitada por ora -- cobertura
  de spend já estabiliza entre min=5 e min=30 (90,1% -> 87,0%), sem ganho
  suficiente para justificar itens com significância estatística menor.

## Nota metodológica: MAE/RMSE pouco informativos com item_key heterogêneo

Baseline avaliado com MAE, RMSE, MAPE (média) e MAPE (mediana). MAPE por
média (18098%/23271%) e dominado por poucos casos de erro percentual
extremo em itens de preco baixo -- nao confiavel como resumo. MAE/RMSE
absolutos (R$ 41.5k/R$ 283.5k) sao pouco informativos porque misturam
itens de escalas de preco muito diferentes numa media so -- item caro
domina a metrica global. MAPE mediana (77,94% validacao, 78,57% teste) e
a metrica mais confiavel deste baseline; serve de referencia a ser
superada por modelos mais sofisticados (Fase 8), nao como resultado final.
Cobertura: ~80% (validacao) e ~69% (teste) das transacoes tem baseline
confiavel disponivel (item_key com >=5 transacoes no treino/2024).