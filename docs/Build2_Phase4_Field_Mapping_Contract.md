# Build 2 — Phase 4: Field Mapping Contract (Deterministic)

## Purpose
Map UI-friendly fields into canonical engine fields BEFORE overlay rule evaluation.
No heuristics. No UI logic. No taxonomy changes.

## Mapping Rules (v1)

### M1 — Contractor monthly income
- Source field: income.monthly_amount
- Target field: role.contractor.monthly_income_usd
- Direction: source → target (one-way copy)
- When applied:
  - IF source exists AND source is not null
  - AND target is missing OR target is null
- Action:
  - Set target = source (exact value)
- Side effects:
  - Do NOT delete or modify source
  - Do NOT change any other fields
- Determinism:
  - If conditions are not met, do nothing.

## Execution Placement
- Run mapping BEFORE overlay rule evaluation.
- Must not modify missing_fields logic or ordering.
