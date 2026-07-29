# Cloud Hooks Matrix Contract

Закон машиночитаемой матрицы Cursor **conversation / cloud hooks** (с 3.11) для T-800 и Cloud Hub.

Источник фактов: [cursor.com/docs/hooks](https://cursor.com/docs/hooks).  
Машина: [`shared/cloud-hooks-matrix.json`](cloud-hooks-matrix.json).

## 1. Закон матрицы

1. Каждый hook в JSON: `name`, `cloud_supported`, `role` (`observe` | `gate_candidate` | `local_only`), `sole_gate_forbidden`, `notes`.
2. Smoke и агенты **не выдумывают** поддержку cloud — только матрица + official docs.
3. При расхождении docs ↔ matrix → обновить matrix (maintainer / factory PATCH), не «обойти» smoke.

## 2. Cloud = command-only

| Правило | Значение |
|---------|----------|
| `policy.cloud_command_based_only` | `true` |
| `policy.forbid_prompt_type_hooks_for_cloud` | `true` |

- В cloud-safe / Hub-ориентированных `hooks.json` допустимы только **command**-хуки (`command` / type command).
- `type: prompt` → **FAIL** в `t800_cloud_hooks_smoke.py`.
- Prompt-хуки не считать cloud-safe даже если event есть в матрице как cloud_supported.

## 3. Fail-open по умолчанию

`policy.default_fail_open: true`

- Не включать enforce «закрыть весь разговор» одним observe-хуком.
- Gate-кандидаты без companion — WARN (не silent PASS как sole gate).
- Local-only events (`sessionStart`, `beforeMCPExecution`) в локальном `hooks.json` → **WARN**, не FAIL (кроме `--require-cloud-safe`).

## 4. Sole conversation gate — запрещён

`policy.forbid_sole_conversation_gate: true`

События с `sole_gate_forbidden: true` (в т.ч. `afterAgentResponse`, `afterAgentThought`, `stop`, `beforeSubmitPrompt`, observe-хуки) **нельзя** объявлять единственным production gate.

- `meta.sole_production_gate` = имя conversation observe/stop **без** companion `beforeShellExecution` / `subagentStart` → **FAIL**.
- Anti-Ralph: `stop` followup loops — gate_candidate, но не sole gate.

Допустимые companion gates (cloud): `beforeShellExecution`, `subagentStart` (`sole_gate_forbidden: false`).

## 5. Smoke script

```bash
python3 scripts/t800_cloud_hooks_smoke.py --hooks PATH [--matrix PATH]
python3 scripts/t800_cloud_hooks_smoke.py --fixture-dir DIR
python3 scripts/t800_cloud_hooks_smoke.py --hooks PATH --require-cloud-safe
```

Фикстуры: `tests/fixtures/cloud-hooks/` (`ok-*` PASS, `bad-*` FAIL).  
Runner: `python3 tests/test_cloud_hooks_smoke.py`.

## 6. Связь с Cloud Hub

- Контракт Hub: [`cloud-hub-setup-contract.md`](cloud-hub-setup-contract.md) § Cloud hooks matrix.
- Пример observe-only: [`docs/examples/cloud-hub/hooks-observe.example.json`](../docs/examples/cloud-hub/hooks-observe.example.json).
- Агент чеклиста: `t-800-cloud-hub-smoke` — Read этого контракта + пункт smoke script / no sole conversation gate / command-based only.

## 7. FORBIDDEN

- Sole production gate на `afterAgentResponse` / `afterAgentThought` / `stop`
- Prompt-type hooks как cloud policy
- Enforce-by-default без явного HITL / отдельного fix-pack
- Выдумывать cloud support для `local_only` events
