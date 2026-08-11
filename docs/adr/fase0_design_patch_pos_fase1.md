# Patch do documento de design — pós-Fase 1

Aplicar as seguintes alterações em `fase0_design_procurement_intelligence.md`.

## 1. Seção 8 — Modelo Dimensional

No bloco de `fact_purchase`, substituir a nota do Ajuste 1 por:

> **Ajuste 1 (revisado pós-Fase 1, ver ADR-0004):** o grão real confirmado é `(purchase_item_id × supplier_key)`, não `purchase_item_id` isolado — Fase 1 mediu 3,38% de duplicidade em `id_compra_item`, parte legítima (múltiplos fornecedores homologados), parte artefato de exportação (deduplicar antes de carregar no Gold).

## 2. Seção 9 — Roadmap

Na linha da Fase 7:

- substituir `2022-2024 → treino`, caso ainda conste como exemplo;
- referenciar o ADR-0003;
- atualizar o objetivo da Fase 7/8 para o split revisado:

**Treino = 2024 / Validação = 2025 / Teste = 2026 (parcial).**

## 3. Seção 10 — Riscos

Substituir o risco #4 por:

> 4. **Split temporal mal calibrado — CONFIRMADO na Fase 1, resolvido via ADR-0003.** Volume de 2022-2023 é ~5-10x menor que 2024-2025 devido à adoção gradual da Lei 14.133, não a variação real de mercado. Split revisado para treino=2024, validação=2025, teste=2026.
