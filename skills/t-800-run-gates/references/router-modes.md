# Router modes (Cost / Balance / Intelligence)

Канон: [`shared/router-cost-policy-contract.md`](../../../shared/router-cost-policy-contract.md).

## Stage → prefer

| Stage | Prefer |
|-------|--------|
| DEEP research | Cost или Balance |
| factory architect / builder | Intelligence или Balance |
| LIGHT / SKIP / PATCH / auditor | Cost или Balance |

## Правила

- `model: inherit` + Router Auto — не pin vendor slug
- Режим Router выбирает человек в UI Cursor
- Агенты только напоминают prefer, не переключают runtime

## Проверка note-gate

```bash
python3 scripts/t800_router_policy_gate.py --plugin-root .
```

Exit 0 + JSON `ok: true` — контракт и эта заметка на месте, маркеры на месте.
