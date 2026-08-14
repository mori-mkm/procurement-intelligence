# Procurement Intelligence Platform

Plataforma de Spend & Price Intelligence construída sobre dados públicos
de compras do PNCP (compras.gov.br), usados como **proxy** para
procurement corporativo. Projeto de portfólio para demonstrar competência
combinada de Data Engineering e Data Science, direcionado a uma vaga
híbrida de Compras/Procurement em instituição financeira.

> **Limitação central, válida para todo o projeto:** os dados são de
> compras públicas, não de procurement bancário real. A metodologia
> (pipeline, benchmarking de preço, detecção de anomalia, savings engine)
> é portátil para sistemas corporativos como SAP Ariba, Coupa, Oracle
> Procurement. Testamos filtrar por instituições financeiras públicas
> (Banco do Brasil, Caixa) -- sem volume rastreável no PNCP apesar de
> habilitação formal desde 2023. A alternativa adotada foi curar um
> subconjunto de categorias de compra que se assemelham a procurement
> corporativo via palavra-chave (ver ADR-0009).

## O problema de negócio

Onde estão as oportunidades de economia dentro das compras, e quais
transações apresentam preço significativamente acima do valor esperado?
