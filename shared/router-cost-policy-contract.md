# Router Cost Policy Contract

Политика Cursor **Router** (`Cost` | `Balance` | `Intelligence`) для отделов T-800.  
Не pin model slug — только `model: inherit` + Router Auto в UI.

## Режимы (UI Cursor)

| Режим | Смысл |
|-------|--------|
| **Cost** | Дешевле / быстрее — длинный fan-out, много specialists |
| **Balance** | Компромисс цена/качество |
| **Intelligence** | Максимум качества кода и архитектуры |

Человек выставляет Router в UI чата; агенты **не** переключают режим runtime.

## Матрица prefer (soft)

| Stage | Prefer | Avoid |
|-------|--------|--------|
| **DEEP** research (`research-lead` + specialists) | Cost или Balance | Intelligence-only по умолчанию |
| factory architect / builder | Intelligence или Balance | Cost-only для сложного design/write |
| LIGHT / SKIP / PATCH repair | Cost или Balance | — |
| auditor / readonly gates | Cost или Balance | — |

## HARD

- Агенты: `model: inherit` (не менять на vendor slug)
- В вызове `Task` **не** передавать `model`
- Router Auto + inherit; эта матрица — guidance, не machine switch

## Связано

- `shared/deep-research-contract.md`
- `shared/loop-engineering-contract.md`
- `skills/t-800-run-gates/references/router-modes.md`
- Gate: `scripts/t800_router_policy_gate.py`

## Версия

- Введён: 2026-07-29 · T-800 **1.21.2**
