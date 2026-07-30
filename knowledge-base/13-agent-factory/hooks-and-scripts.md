---
title: "Hooks и скрипты для субагентов"
source: https://cursor.com/docs/hooks
audience: advanced
tier: 4
last_synced: 2026-07-30
provenance: manual
author: t-800
---

# Hooks и скрипты

## Когда hook, а не subagent

| Hook | Сценарий |
|------|----------|
| `preToolUse` | Gate действий до вызова инструмента: разрешить, запретить или подменить ввод (`updated_input`) |
| `postToolUseFailure` | Трекинг падений инструментов (`error` / `timeout` / `permission_denied`) |
| `subagentStart` | Разрешить/запретить запуск определённых Task |
| `subagentStop` | Цепочка: после auditor → уведомить integrator |
| `sessionStart` | Проверить health плагина |
| `afterFileEdit` | Форматтеры и учёт кода, написанного Agent |
| `beforeSubmitPrompt` | Блок секретов в промптах |
| `workspaceOpen` | Подгрузить дополнительные плагины (`pluginPaths`) при открытии workspace |

## Расположение

| Тип | Путь |
|-----|------|
| Проект | `.cursor/hooks.json`, `.cursor/hooks/*` |
| Пользователь | `~/.cursor/hooks.json` |

## Пример: эталон из репо T-800 (hooks.json плагина)

Реальный `hooks.json` плагина — `preToolUse` с matcher по именам инструментов:

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      { "command": "bash hooks/t-800-session-bootstrap.sh", "timeout": 120 }
    ],
    "preToolUse": [
      {
        "command": "bash hooks/before-artifact-edit.sh",
        "matcher": "Write|StrReplace|EditNotebook",
        "timeout": 15
      }
    ]
  }
}
```

`matcher` — это **точное имя инструмента или regex** (`Write|StrReplace|EditNotebook`), а не выражение вида `tool == "..."`. Для `preToolUse`/`postToolUse` matcher сравнивается с именем инструмента (`Shell`, `Read`, `Write`, `Task`, `MCP:<tool>`); для shell-событий — со строкой команды; для `subagentStart` — с типом субагента.

## Скрипты T-800 Factory

| Скрипт | Назначение |
|--------|------------|
| `install-plugin.ps1` | Деплой в `~/.cursor/` |
| `verify-install.ps1` | Проверка установки |
| `validate-agents.ps1` | Frontmatter, name, description |
| `audit-agent-graph.ps1` | Реестр vs файлы, связи |
| `register-agent.ps1` | Добавить запись в registry |

## Как писать scripts плагина

- **Парность платформ:** конвенция репо — пара `.sh` (macOS/Linux) + `.ps1` (Windows) для пользовательских операций. Текущее состояние `scripts/`: 19 файлов `.sh`, 11 файлов `.ps1`, 26 файлов `.py` — полного покрытия 1:1 пока нет.
- **Stdlib-only:** bash + coreutils или `python3` стандартная библиотека. Внешние зависимости (`jq`, `pyyaml`, пакеты pip) не используем — у пользователя их может не быть.
- **Stdin JSON-контракт:** hook-скрипт читает JSON события со stdin (одним документом) и пишет JSON-ответ в stdout. Вход всегда содержит `hook_event_name`, `cursor_version`, `workspace_roots`; дальше — поля конкретного события.
- **Exit codes:** `0` — успех (Cursor читает JSON из stdout), `2` — блок действия (равносильно `permission: "deny"`), любой другой код — hook упал, действие пропускается (fail-open, если не выставлен `failClosed: true`).
- Логи и временные файлы — в `/tmp`, не в репозиторий.

## Skill со скриптами

Skill может включать `scripts/` — Agent запускает их по инструкции в SKILL.md. Для maintainer-операций (sync, audit) — skill с `disable-model-invocation: true`.

## Безопасность hooks

- Нет удаления без backup
- Нет секретов в hook-файлах
- `failClosed` только когда критично

## Release playbook (версии плагина)

- Канон канала обновлений — `shared/release-channel.json`: `github_repo`, `plugin_json_url`, `releases_url`, `auto_update` (sessionStart-хук `scripts/t800-auto-version-check.sh`, TTL 6ч, контракт `shared/auto-update-contract.md`)
- Версия живёт в `.cursor-plugin/plugin.json` (поле `version`, semver)
- Практика из git log: коммиты «Release vX.Y.Z: …», теги `v1.20.1`…`v1.22.1`, запись в `knowledge-base/CHANGELOG.md` на каждую версию, GitHub Release (практика с v1.20.1)
- PATCH-волны fix-pack идут **без bump версии** — bump отдельной фазой (факт волны w3)

Флоу релиза:

1. Bump `version` в `.cursor-plugin/plugin.json`
2. Запись в `knowledge-base/CHANGELOG.md`
3. Коммит `Release vX.Y.Z: …`
4. Тег `vX.Y.Z`
5. Push main + tags
6. GitHub Release
7. Клиенты получают автообновление через sessionStart-хук по `release-channel.json`

## Ссылка

https://cursor.com/docs/hooks
