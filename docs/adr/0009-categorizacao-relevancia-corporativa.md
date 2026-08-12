# ADR-0009: Categorizacao de relevancia para procurement corporativo

## Status
Aceito

## Contexto
O projeto usa compras publicas do PNCP como proxy para procurement
corporativo (limitacao ja documentada na Fase 0). Mas boa parte do volume
observado (Fase 2/3) reflete perfil tipico de prefeitura/hospital/escola
(alimentos, insumos medicos) -- categorias que uma instituicao financeira
nunca compraria, o que enfraquece a relevancia narrativa do projeto para o
publico-alvo (vaga de Procurement em instituicao financeira).

Investigamos duas alavancas para aproximar o escopo do perfil de compra
corporativo:

1. Filtrar por orgao comprador (instituicoes financeiras publicas
   especificas, como Banco do Brasil e Caixa). Testado por CNPJ completo,
   CNPJ base e busca textual por razao social nos arquivos anuais 2024 e
   2025 -- nenhum registro encontrado em nenhum dos tres testes, apesar de
   BB e Caixa estarem formalmente habilitados a publicar no PNCP desde
   31/10/2023. Descartado: habilitacao regulatoria nao se traduziu em
   volume publicado rastreavel nesse dataset.

2. Filtrar por categoria de produto/servico. Testamos primeiro os campos
   estruturados de classificacao do PNCP (`codigo_grupo`,
   `item_categoria_id_pncp`) e ambos se mostraram nao confiaveis:
   `codigo_grupo` ausente em ~92% dos registros; `item_categoria_id_pncp`
   presente em 100% dos casos mas constante (valor 3 / "Informatica (TIC)")
   independente do conteudo real do item -- terceiro campo de classificacao
   estruturada do PNCP a falhar neste projeto (ver tambem CATMAT, ADR-0006).

Diante disso, testamos classificacao por palavra-chave sobre
`descricao_resumida` (texto livre), a unica fonte que se mostrou confiavel
ate agora neste dataset. Duas rodadas de correcao foram necessarias:
- V1: termos isolados demais (`monitor`, `servidor`, `rede`) geraram falso
  positivo (ex: "Caixa Acustica" capturada como TI por causa de "monitor de
  palco"; "servidor publico" capturado por "servidor").
- V2 (corrigida): termos compostos mais especificos eliminaram os falsos
  positivos, mas a normalizacao de acentuacao estava ausente, gerando falso
  negativo (`"escritorio"` no codigo nao batia com `"Escritorio"` no dado
  real) -- categorias inteiras (`Mobiliario`, `Locacao de Veiculos`) cairam
  para zero artificialmente.
- V3 (final): normalizacao de acentuacao no texto de origem antes da
  comparacao, mantendo `\b` para evitar substring espuria.

Resultado validado em tres medicoes independentes: dois dias de amostra
(2,33% e 2,57%) e o arquivo anual completo de 2025 via DuckDB (2,29%, ou
108.534 de 4.736.611 registros) -- consistente o suficiente para confiar.

## Decisao
Adicionar duas colunas nao-destrutivas ao Silver, seguindo o mesmo padrao
ja usado para unidade de medida (ADR-0005) e conflito de resultado:

- `categoria_relevante`: nome da categoria (das 8 curadas) cuja palavra-
  chave bateu na descricao, ou None.
- `is_categoria_relevante`: booleano derivado, para filtro rapido.

Nenhuma linha e removida do Silver. Quem consumir o dado (Spend Analytics,
dashboard, README) decide se filtra por `is_categoria_relevante` para o
recorte "relevante para banco", ou usa o dataset completo para demonstrar
a metodologia em escala ampla. As duas visoes coexistem no mesmo pipeline.

## Consequencias
- A lista de palavras-chave e curadoria manual, sujeita a vies de quem
  escreveu -- documentar isso explicitamente no README, nao apresentar
  como classificacao objetiva.
- TI/Informatica domina o volume capturado (~60-65% do total nas amostras)
  -- qualquer analise que use o recorte relevante vai ser naturalmente
  dominada por essa categoria; vale mencionar isso ao interpretar
  resultados de Spend Analytics feitos sobre o subconjunto filtrado.
- `Locacao de Veiculos` teve volume quase nulo nas amostras diarias (0-1
  transacao) -- candidato a remocao da lista curada se o padrao se
  confirmar em mais amostras, mas mantido por ora sem numero suficiente
  para decidir.
- Lista pode (e deve) crescer conforme mais categorias relevantes forem
  identificadas -- e curadoria viva, nao fechada.

## Alternativas consideradas
- **Filtrar por instituicao financeira publica compradora:** rejeitada,
  ver Contexto -- sem volume rastreavel.
- **Usar campos estruturados de categoria do PNCP:** rejeitada -- dois
  campos testados, ambos nao confiaveis (ver Contexto).
- **Filtro destrutivo (remover linhas nao-categorizadas do Silver):**
  rejeitada -- perde a capacidade de demonstrar a metodologia em escala
  ampla, que e parte do valor do projeto (ver Fase 0, limitacao de dado
  proxy). O nao-destrutivo preserva as duas narrativas.