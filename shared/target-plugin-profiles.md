# T-800 — профили целевого проекта

**T-800 — generic factory** для любого Cursor plugin. Product-специфика живёт в декларативных
discovery-профилях **`profiles/<id>.md`** и адаптерах **`adapters/<id>/`**.

```bash
bash scripts/discover-target-project.sh --workspace "<WORKSPACE>"
```

Контракты: `shared/project-discovery-contract.md`, `shared/project-memory-contract.md`

## Профили (после discovery)

| profile | plugin_root (куда писать agents/skills) | memory (отчёты прогона) | Release | Adapter |
|---------|-------------------------------------------|-------------------------|---------|---------|
| declared adapter profile | из профиля: env / workspace self (installed = readonly) | `markers.memory_dir_present` | из `release_handoff` профиля | **из поля `adapter`** |
| `generic-plugin` | workspace или marker | `{slug}-memory/` | по README / marker | none |
| `self-t800` | `t-800-agent/` | `t-800-memory/` | `install-plugin.sh` + Reload | none |
| `marker` | из `project-memory.marker.json` | из marker | из marker | из совпавшего профиля |

Product-профили декларируют маркеры детекта (`require` / `any_of` / `memory_dir_present`),
`memory_dir`, `release_handoff`, `plugin_root` (env_key / readonly_fallback / never_canonical)
и `adapter` — см. `profiles/*.md`. Пример: adapter `<id>` (см. `adapters/<id>/`).

## Устаревшие ID (миграция брифов)

| Старый `target_plugin` | Новый |
|--------------------------|-------|
| legacy product alias | нормализуй в declared profile по discovery (matcher `adapters/<id>/profiles.py`) |
| `t-800-agent` | `self-t800` |
| `generic-plugin` | без изменений |

Machine matcher adapter-профилей: `adapters/<id>/profiles.py` (путь из `adapters/<id>/adapter.manifest.json` → `entrypoints.profile_matcher`).

## Declared adapter profile (правка продукта из клиента)

1. Discovery: маркеры из `profiles/<id>.md`
2. `plugin_root` = env_key профиля (git checkout) — **не** sibling guess как SoT
3. Installed `~/.cursor/plugins/local/<id>` — только readonly fallback (`write_allowed=false`)
4. **Запрещено** писать в installed local
5. Fragments / handoffs → memory профиля (`factory-handoffs/<run-id>.json`)
6. Handoff: `release_handoff` из discovery (не выполнять из T-800)

## generic-plugin

1. Нет memory → `bash scripts/init-project-memory.sh --slug <name>`
2. Integrator пиши в `agents/`, `skills/`, `commands/` относительно `plugin_root`
3. **Без** adapter release/smoke/registries

## Выбор (architect)

Discovery `needs_user_question: true` → один вопрос:

«Укажите папку git checkout плагина (plugin_root) или откройте workspace плагина.»

Не угадывать путь молча. Не брать sibling-пути как canonical.

## plugin_root env

Ключ и env-файл резолвятся из профиля (`plugin_root.env_key` / `plugin_root.env_file`),
без source файла секретов — только grep ключа.
