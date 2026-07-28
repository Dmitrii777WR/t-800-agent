# Lesson: Cursor silent-drop битого YAML frontmatter → Invalid enum

**Дата:** 2026-07-21  
**Источник:** ActiveZone incident `T800-INCIDENT-figma-frontmatter-yaml-invalid-enum`  
**Gate:** `scripts/t800_agent_frontmatter_yaml_gate.py`

## Симптом

`Task(some-new-agent)` → `Invalid enum`. Файлы `agents/*.md` на диске есть, Reload Window «не помогает».

## Корневая причина

Битый YAML в frontmatter. Частый паттерн factory emit:

```yaml
# WRONG — никогда не emit
description: "Short line."
  Use when …
  Do NOT use when …
```

После закрытых кавычек строки `Use when` / `Do NOT` — невалидный block mapping. Cursor **молча выкидывает** такого агента из каталога Task → в enum его нет → `Invalid enum`.

## Что НЕ чинит

- Reload Window
- Reinstall plugin без исправления YAML
- `validate-agents.sh` без PyYAML-parse (дыра закрыта machine gate)

## CORRECT emit

```yaml
description: >
  Short.
  Use when …
  Do NOT use when …
```

Или одна строка `description: "… Use when … Do NOT …"` **без** продолжений на следующих строках.

## Защита T-800

1. Builder: только `>` fold или one-line; после Write — YAML gate.
2. Prompt-auditor: Frontmatter YAML parse PASS.
3. Factory-auditor: `frontmatter_yaml: PASS|FAIL` — FAIL блокирует delivery.
4. `t800_run_gate.py --require-frontmatter-yaml` (auto-ON при `--strict-create` + `--plugin-root`).

Контракт: `shared/prompt-craft-contract.md`.
