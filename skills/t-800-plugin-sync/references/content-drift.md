# CONTENT_DRIFT — что сравнивать

Цель: SoT (git `plugin_root`) ↔ live `~/.cursor/plugins/local/t-800-agent`.

## Сравнивать (типично)

- `agents/`, `commands/`, `skills/`, `rules/`, `hooks*`, `scripts/`
- `shared/`, `registry/`, `.cursor-plugin/plugin.json`
- Критичные templates

## Fail meanings

| Сигнал | Смысл |
|--------|--------|
| `CONTENT_DRIFT` | live ≠ SoT — нужен apply MIR |
| missing live | install не выполнен |
| version pin stale | marketplace/old copy — не first fix |

## Never

- Писать в `~/.cursor/agents`, `~/.cursor/skills`, `~/.cursor/rules` как «зеркало плагина»
- Править live в обход SoT без последующего commit в git checkout
- Считать marketplace reinstall заменой sync --check

Контракт: `shared/auto-update-contract.md`.
