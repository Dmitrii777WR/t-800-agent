# PATCH constraints

Контракт: `shared/fix-pipeline-contract.md`.

## Hard

1. Write **только** пути из `files[]` pack.
2. Не создавать новых research/brain агентов в PATCH.
3. Не объявлять PASS без `t800_run_gate.py` (exit 0).
4. Main chat / skill не правят agents|skills|commands|rules|hooks — только factory.
5. Не переключаться на полный DEEP `/t800-start`, если задача — узкий PATCH.

## Soft

- Research SKIP/LIGHT по умолчанию; DEEP только если pack явно просит.
- Brain: обычно 1 domain.
- После PASS — STATE Gates + Completed; опционально loop-queue close.

## Out of scope

Production сайты/deck клиента, secrets в git, bump version без approve Директора.
