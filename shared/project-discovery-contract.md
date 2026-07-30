# T-800 — обнаружение целевого проекта

Отдел **универсален**: он не привязан к одному плагину. Перед любой сборкой агентов определи **куда писать код** и **где хранить память прогона**.

## Два корня (не путать)

| Понятие | Что это | Пример |
|---------|---------|--------|
| **workspace_root** | Папка, открытая в Cursor сейчас | `Мой сайт/`, `MyPlugin/` |
| **plugin_root** | Git/checkout плагина, куда пишутся `agents/`, `skills/`, `commands/` | `$<PLUGIN_ENV_KEY>` из профиля, `t-800-agent/` |
| **memory_path** | Папка памяти **этого** workspace или сессии | `plugin-memory/`, `{slug}-memory/` |

**Закон:** память прогона T-800 живёт в **memory_path целевого контекста**, не «всегда в t-800-memory».  
`t-800-memory/` — только если workspace **разрабатывает сам T-800 Agent** (см. marker ниже).

## Алгоритм (BOOT каждого `/t800-start`)

0. **Выбор плагина:** `list-target-plugins.sh` + текст пользователя (`shared/target-selection-contract.md`)
1. Запусти discovery:
   ```bash
   bash scripts/discover-target-project.sh --workspace "<WORKSPACE_ROOT>"
   ```
2. Если `needs_user_question: true` или несколько плагинов без указания в тексте — **один** вопрос: «Для какого плагина?» (список из `known-plugins.json`)
3. Прочитай `memory_path/run-manifest.json` (если есть) — контекст прошлых прогонов.
4. Передай в factory YAML-блок `target_context` (см. `shared/t-800-factory-contract.md`).

## Маркер проекта (рекомендуется для новых плагинов)

Файл в **корне workspace** (или рядом с `.cursor-plugin/`):

```text
project-memory.marker.json
```

```json
{
  "slug": "my-plugin",
  "memory_dir": "my-plugin-memory",
  "plugin_root": ".",
  "release_handoff": null,
  "knowledge_vault_path": null
}
```

| Поле | Назначение |
|------|------------|
| `slug` | Короткое имя плагина |
| `memory_dir` | Папка памяти относительно workspace |
| `plugin_root` | `.` или подпапка с `.cursor-plugin/plugin.json` |
| `release_handoff` | Команда release целевого плагина или null |
| `knowledge_vault_path` | Optional. Absolute path **или** relative от workspace root → target vault (Obsidian-style). `null` / отсутствует → discovery emit `null`. Relative → absolute от workspace root. **Target vault runtime-only:** читать можно; **forbid** копировать содержимое vault в `agents/`, `skills/`, `knowledge-base/`, `shared/`, `commands/` плагина. Полный закон: `shared/project-memory-contract.md`. |

T-800 **не создаёт** marker в чужих проектах без запроса. Для нового плагина — `bash scripts/init-project-memory.sh`.

## Авто-распознавание (без marker)

| Сигнал | profile | plugin_root | memory_dir |
|--------|---------|-------------|------------|
| Маркеры из `profiles/<id>.md` (`require` + `any_of` + `memory_dir_present`) | declared profile | env / readonly fallback / workspace self — из поля `plugin_root` профиля | `memory_dir` профиля |
| `.cursor-plugin/plugin.json` + `{name}-memory/` | `generic-plugin` | workspace или marker | `{name}-memory/` |
| Marker `t-800-agent` / memory `t-800-memory` | `self-t800` | `t-800-agent/` | `t-800-memory/` |

Product-профили декларативны: `profiles/*.md` (один fenced ```json блок — SoT маркеров).
Поле `adapter` профиля → discovery `adapter`; специфика адаптера — `adapters/<id>/`.

## Сценарии оператора

### A. Declared adapter profile (разработка продукта с адаптером)

- workspace = checkout плагина продукта
- profile/plugin_root/memory — из `profiles/<id>.md`
- Release: `release_handoff` профиля (выполняется вне T-800)
- Пример: adapter `<id>` (см. `adapters/<id>/`)

### B. Клиент продукта с адаптером — правка агентов из клиента

- workspace = клиент (memory dir из профиля)
- plugin_root = env_key профиля (git checkout, **не** installed readonly fallback)
- memory прогона = `<memory_dir>/fragments/` + `run-manifest.json`
- После integrator: handoff `release_handoff` в workspace плагина

### C. Новый плагин Foo

- Создать workspace, `init-project-memory.sh --slug foo`
- Получить `foo-memory/run-manifest.json`, `factory-briefs/`

### D. Разработка T-800 Agent

- workspace = `T-800 AGENT/`
- marker или convention: `t-800-memory/`, plugin_root = `t-800-agent/`

## Запреты

- Не писать артефакты в installed readonly fallback `~/.cursor/plugins/local/<id>` (перезаписывается sync)
- Не assume `target_plugin=t-800-agent` без discovery
- Не смешивать memory разработки плагина (`plugin-memory/` в checkout) и memory клиента (`{slug}-memory/`)

## Скрипты

| Скрипт | Назначение |
|--------|------------|
| `discover-target-project.sh` | JSON: workspace, plugin_root, memory_path, profile, `knowledge_vault_path` (`null` если не задано) |
| `list-target-plugins.sh` | Список checkout'ов из `~/.t800/known-plugins.json` |
| `init-project-memory.sh` | Scaffold memory для нового плагина |

Discovery JSON: поле `knowledge_vault_path` — `null` или absolute string (relative из marker уже resolved от workspace root).

Контракт памяти: `shared/project-memory-contract.md`
