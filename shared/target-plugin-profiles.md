# T-800 — профили целевого проекта

**T-800 — generic factory** для любого Cursor plugin. Teya — отдельный продукт; интеграция только через **`adapters/teya/`** (`shared/teya-adapter-contract.md`).

```bash
bash scripts/discover-target-project.sh --workspace "<WORKSPACE>"
```

Контракты: `shared/project-discovery-contract.md`, `shared/project-memory-contract.md`

## Профили (после discovery)

| profile | plugin_root (куда писать agents/skills) | memory (отчёты прогона) | Release | Adapter |
|---------|-------------------------------------------|-------------------------|---------|---------|
| `teya-plugin-dev` | workspace TeyaPlugin (git) | `plugin-memory/` | handoff `/teya-release-sync` | **teya** |
| `teya-client` | `$TEYA_PLUGIN_ROOT` (env/marker; installed = readonly) | `teya-memory/` в клиенте | handoff → TeyaPlugin | **teya** |
| `generic-plugin` | workspace или marker | `{slug}-memory/` | по README / marker | none |
| `self-t800` | `t-800-agent/` | `t-800-memory/` | `install-plugin.sh` + Reload | none |
| `marker` | из `project-memory.marker.json` | из marker | из marker | teya if Teya checkout |

## Устаревшие ID (миграция брифов)

| Старый `target_plugin` | Новый |
|--------------------------|-------|
| `teya-pro` | **legacy alias** — активирует brain-teya + adapter; нормализуй в `teya-plugin-dev` или `teya-client` по discovery |
| `t-800-agent` | `self-t800` |
| `generic-plugin` | без изменений |

Machine: `from adapters.teya.profiles import match_brain_teya, is_teya_profile`

## teya-client (правка Teya из клиента)

1. Discovery: `teya-memory/` в workspace
2. `plugin_root` = `$TEYA_PLUGIN_ROOT` (git checkout) — **не** sibling `../TeyaPlugin` как SoT
3. Installed `~/.cursor/plugins/local/teya` — только readonly fallback (`write_allowed=false`)
4. **Запрещено** писать в installed local
5. Fragments / handoffs → `teya-memory/` (`factory-handoffs/<run-id>.json`)
6. Handoff: «Открой TeyaPlugin → `/teya-release-sync`» (не выполнять из T-800)

## teya-plugin-dev

1. workspace = TeyaPlugin git
2. Читать BOOT: `plugin-memory/HANDOFF.md`
3. Post-factory: `plugin-memory/factory-handoffs/` + `t800_teya_onboarding_gate.py`
4. Run manifest эфемерно: `.teya-plugin-run/` **или** traces в `plugin-memory/`

## generic-plugin

1. Нет memory → `bash scripts/init-project-memory.sh --slug <name>`
2. Integrator пишет в `agents/`, `skills/`, `commands/` относительно `plugin_root`
3. **Без** Teya release/smoke/registries

## Выбор (architect)

Discovery `needs_user_question: true` → один вопрос:

«Укажите папку git checkout плагина (plugin_root) или откройте workspace плагина.»

Не угадывать путь молча. Не брать sibling `../TeyaPlugin` как canonical.

## TEYA_PLUGIN_ROOT

`~/.teya/teya.env.global` или `teya-memory/teya.env.local` — только для Teya.
