# Prompt Eval Contract (Phase 4)

Узкий **behavioral** gate для критичных промпт-поверхностей T-800.  
Не полный CI suite и не замена `t-800-prompt-auditor` / factory-auditor.

## Цель

Проверить, что в живых файлах плагина **остались** обязательные маркеры
(`must_contain`) и **нет** запрещённых строк (`must_not_contain`).

## Surface (v1.21.3)

| id | file | Смысл |
|----|------|--------|
| `factory_bypass_rule` | `rules/t-800-mandatory-routing.mdc` | BLOCKER + `Task(t-800-factory)` |
| `loop_conductor_open_only` | `agents/t-800-loop-conductor.md` | approve только `status=open` / open only |
| `intake_clarifier_no_websearch` | `agents/t-800-intake-clarifier.md` | `Do NOT WebSearch` / не invent answers |

Фикстура: `tests/fixtures/prompt-eval/cases.json`.  
Строки `must_contain` — **дословные** фрагменты из текущих файлов (не paraphrases).

## Machine gate

```bash
python3 scripts/t800_prompt_eval_gate.py --plugin-root .
python3 scripts/t800_prompt_eval_gate.py --plugin-root . --cases PATH
python3 scripts/t800_prompt_eval_gate.py --plugin-root . --promptfoo
```

| Режим | Поведение |
|-------|-----------|
| default | встроенный checker; stdout JSON `{ok, cases, passed, failed, errors}` |
| `--promptfoo` | если CLI `promptfoo` нет → **WARN skip**, не FAIL; SoT остаётся built-in |

Exit **0** = PASS; **1** = FAIL.

Тест: `python3 tests/test_prompt_eval_gate.py`.

## Ограничения

- **Не** добавлять npm-зависимость `promptfoo` в `package.json` (optional CLI only)
- Gate **читает** промпты; не меняет смысл агентов/rules
- Не sole gate для CREATE — companion к `t800_run_gate.py` / verify-install

## Связано

- `scripts/t800_prompt_eval_gate.py`
- `skills/t-800-run-gates/references/gate-matrix.md`
- `shared/t-800-agent-quality-contract.md`
- `shared/loop-engineering-contract.md`

## Версия

- Введён: 2026-07-29 · T-800 **1.21.3**
