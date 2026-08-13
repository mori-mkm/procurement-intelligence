
# ADR-0014: Flag de outlier de valor (unit_price/quantity) via modified z-score

## Status
Aceito

## Contexto
Investigacao de HHI para "Limpeza/Facilities" revelou concentracao
implausivel (99,59% num unico fornecedor). Causa raiz: uma unica
transacao com valor_total = R$ 2,29 trilhoes (unit_price=239.678,46,
quantity=9.556.390) -- lancamento incorreto na fonte, nao gasto real.
Investigacao expandida ao fact_purchase inteiro (2024-2026): as 20
maiores transacoes (0,0003% de 5.788.938 linhas) concentravam **85,34%**
do spend total reportado. Dois padroes de erro observados: preco unitario
absurdo com quantidade normal, e quantidade absurda com preco normal --
nenhum e capturado checando so total_price isoladamente.

## Decisao
flag_value_outliers (gold.py), chamada dentro de build_fact_purchase:
- Modified z-score (mediana/MAD, Iglewicz & Hoaglin) em vez de z-score
  classico (media/desvio) -- este ultimo e distorcido pelo proprio
  outlier extremo que se quer detectar.
- Checa unit_price e quantity SEPARADAMENTE, em escala log, agrupado por
  item_key -- captura os dois padroes de erro observados.
- min_group_size=5: itens com menos transacoes nao sao avaliados
  estatisticamente (z fica NaN, nao flagado) -- sem base estatistica
  suficiente para um item raro.
- z_threshold=3.5, valor de referencia padrao da literatura.
- Nao remove linha nenhuma -- flag nao-destrutiva (mesmo padrao de
  unit_flag, categoria_relevante, resultado_conflitante).
- src/analytics/spend_analytics.py exclui linhas flagadas por padrao em
  todas as agregacoes (Spend por categoria, HHI, Curva ABC) -- mesma
  logica ja aplicada a resultado_conflitante em compute_spend_total
  (ADR-0010).

## Consequencias
- Todo spend total calculado ANTES desta correcao (incluindo R$ 7,85 tri
  reportado no pipeline combinado 2024-2026) estava inflado por erro de
  lancamento, nao representa gasto publico real -- deve ser descartado e
  recalculado.
- Itens raros (poucas transacoes) nao sao avaliados -- limitacao
  documentada, nao escondida. Se um outlier extremo aparecer num item
  raro, nao sera flagado automaticamente.
- Nao investigamos a causa exata dos lancamentos incorretos na fonte
  (confusao de unidade de quantidade, erro de digitacao de preco) -- fica
  como hipotese nao confirmada.
- fact_purchase precisa ser reconstruido (pipeline completo) para as
  novas colunas existirem.

## Alternativas consideradas
- **Z-score classico (media/desvio padrao):** rejeitada -- distorcido
  pelo proprio outlier extremo, poderia mascarar exatamente o caso mais
  grave (R$ 2,9 tri).
- **Corte absoluto de valor (ex: total_price > R$ 1 bi):** rejeitada --
  contratos publicos legitimos de grande porte (obras de infraestrutura)
  podem legitimamente passar de centenas de milhoes; corte fixo arriscaria
  descartar gasto real.
- **Checar so total_price:** rejeitada -- nao distingue outlier de preco
  de outlier de quantidade, informacao util para quem for investigar caso
  a caso depois.

## Nota final sobre flag_value_outliers (Fase 6, encerrado)

Apos 4 rodadas de refinamento (unit_price/quantity isolados -> +total_price
combinado), o metodo (modified z-score por item_key) continua deixando
passar outliers legitimos quando o item_key agrupa contratos de escala
muito diferente sob o mesmo texto (ex: "pericia, laudo e avaliacao",
"prestacao de servicos bancarios", "concessao de servico publico") --
alguns desses valores extremos podem ate ser reais (contratos publicos de
grande porte existem), nao so erro de lancamento.

Decisao: aceitar a limitacao. flag_value_outliers funciona bem para casos
de erro de digitacao evidente (confirmado: R$2,9tri e R$2,29tri removidos).
Para qualquer relatorio de spend total agregado, aplicar adicionalmente um
corte por percentil global (nao por grupo) como camada extra de seguranca,
implementado em compute_spend_by_category. Nao investigar mais esta classe
de problema -- rendimento decrescente, prioridade e avançar para Fase 7.

## Correcao final: segunda camada por mediana global (Fase 6, fechamento)

flag_value_outliers (por item_key, z-score) nao convergia para 100% de
cobertura apos 4 rodadas -- itens com item_key generico (misturando
contratos de escala muito diferente sob o mesmo texto, ex: "pericia,
laudo e avaliacao", "prestacao de servicos bancarios") continuavam
deixando passar valores extremos.

Adicionada flag_extreme_by_global_median (spend_analytics.py): compara
total_price contra 1000x a mediana global de total_price entre linhas ja
nao-flagadas por flag_value_outliers. Mais simples e robusta que o
z-score por grupo -- nao depende da qualidade do agrupamento por
item_key. Aplicada dentro de _exclude_flagged_rows, usada por todas as
funcoes de spend_analytics.py.

Resultado: HHI de todas as categorias caiu para faixa "nao concentrado"
ou "moderadamente concentrado" -- plausivel para mercado nacional com
milhares de fornecedores por categoria (antes, varias categorias
mostravam concentracao de monopolio, artefato dos outliers).

Ressalva honesta: nao ha garantia de que 100% dos outliers genuinos foram
removidos -- o corte de 1000x a mediana e uma heuristica pragmatica, nao
uma prova estatistica de limpeza completa. Contratos publicos legitimos
de grande porte (obras, concessoes) podem ocasionalmente exceder esse
limite e ser excluidos por engano, ou algum outlier menor pode ainda
passar. Aceito como trade-off razoavel para o MVP -- nao investigar mais.