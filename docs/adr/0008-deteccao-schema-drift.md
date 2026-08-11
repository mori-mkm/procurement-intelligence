# ADR-0008: Detecção de schema drift na camada Bronze

## Status
Aceito

## Contexto
Comparando os 4 dias de amostra real da Fase 2, o arquivo de 22/mai/2026
apresentou 57 colunas em vez das 56 vistas nos outros 3 dias — uma coluna
nova, `COD_RESULTADO_ITEM`, apareceu sem qualquer aviso prévio na fonte.
Nenhuma das funções de qualidade existentes até este ponto
(`build_bronze_quality_report`) detectava isso: elas leem o CSV como vier e
operam sobre colunas esperadas, ignorando silenciosamente colunas novas e
não alertando sobre colunas que eventualmente desaparecessem.

É dado público mantido por terceiros — mudança de schema sem aviso é um
risco real e recorrente, não um evento hipotético. Se Silver ou Gold
assumirem schema fixo em algum ponto, uma mudança como essa quebra
silenciosamente (coluna nova ignorada) ou ruidosamente (coluna esperada
ausente, `KeyError`).

## Decisão
Adicionar checagem explícita de schema drift na Etapa 2 (Bronze
validation), comparando o conjunto de colunas do arquivo do dia contra um
schema de referência versionado no repositório
(`src/quality/reference_schema.json`).

Regras da checagem:
- **Não trava a ingestão.** Schema drift é logado como achado no relatório
  de qualidade, não como erro fatal — não temos controle sobre a fonte.
- Reporta separadamente colunas novas (no arquivo, ausentes na referência)
  e colunas ausentes (na referência, ausentes no arquivo).
- Schema de referência inicial = as 56 colunas observadas em 01/dez/2025,
  o primeiro dia validado cronologicamente entre os 4 medidos na Fase 2.
- Atualização do arquivo de referência é **manual**, feita quando uma
  mudança de schema for confirmada como intencional/permanente — não a
  cada drift pontual, para não mascarar ruído real de mudança genuína.

## Consequências
- Precisa manter `reference_schema.json` versionado no Git — carga de
  manutenção pequena, mas real e recorrente.
- Decisão de "promover" uma coluna nova para o schema de referência é
  manual e deliberada, não automática — evita que um drift pontual vire
  silenciosamente o novo normal sem revisão.

## Alternativas consideradas
- **Travar a ingestão em qualquer schema drift:** rejeitada — dado público
  muda sem aviso; travar geraria falha constante sem alternativa real de
  correção rápida da nossa parte.
- **Ignorar diferenças de schema:** rejeitada — é exatamente o que estava
  acontecendo até este ADR, e foi assim que passou despercebido.
