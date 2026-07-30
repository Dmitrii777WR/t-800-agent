---
title: "plugin.json — манифест плагина"
audience: advanced
tier: 4
last_synced: 2026-07-30
provenance: manual
author: t-800
source: https://cursor.com/docs/plugins
---

# plugin.json — манифест плагина

## Простыми словами

`plugin.json` в папке `.cursor-plugin/` — «паспорт» плагина: Cursor читает его первым и понимает, как плагин называется и где лежат его компоненты (rules, skills, agents, commands, hooks). Обязательное поле одно — `name`, остальное добавляете по мере надобности.

## Поля манифеста

| Поле | Обязательность | Что значит |
|------|----------------|------------|
| `name` | **обязательное** | Идентификатор плагина: lowercase, kebab-case (буквы, цифры, дефисы, точки), начинается и заканчивается буквой или цифрой. Примеры: `my-plugin`, `prompts.chat` |
| `displayName` | нет | Человекочитаемое имя. В официальной схеме не описано; живой пример — эталон `.cursor-plugin/plugin.json` этого репозитория, schema gate T-800 его допускает |
| `version` | нет | Семантическая версия, например `1.0.0` |
| `description` | нет | Краткое описание назначения плагина |
| `author` | нет | Объект: `name` (обязательно внутри объекта), `email` (опционально) |
| `license` | нет | Идентификатор лицензии, например `MIT` |
| `homepage` | нет | URL страницы плагина |
| `repository` | нет | URL репозитория плагина |
| `keywords` | нет | Массив тегов для поиска и категоризации |
| `rules` | нет | Путь (строка или массив) к файлам/папкам rules |
| `skills` | нет | Путь (строка или массив) к папкам skills |
| `agents` | нет | Путь (строка или массив) к файлам/папкам agents |
| `commands` | нет | Путь (строка или массив) к файлам/папкам commands |
| `hooks` | нет | Путь к hooks-конфигу или inline-конфиг hooks |

Есть и другие опциональные поля (`logo`, `mcpServers`, `variables`) — см. официальный reference.

Если пути компонентов не указаны, Cursor сам находит их в папках по умолчанию (`rules/`, `skills/`, `agents/`, `commands/`, `hooks/hooks.json`). Путь, указанный в манифесте, **заменяет** автопоиск для этого типа компонентов.

## Минимальный пример

```json
{
  "name": "my-plugin",
  "description": "Инструменты разработки <owner>",
  "version": "1.0.0",
  "author": { "name": "<owner>" }
}
```

Живой эталон — манифест этого репозитория `.cursor-plugin/plugin.json`: поля `name`, `displayName`, `description`, `version`, `keywords`, `author` и пути `rules`/`skills`/`agents`/`commands`/`hooks`.

## Как валидируется

- Marketplace review требует валидный `.cursor-plugin/plugin.json`: все пути относительные и существующие (без `..`, без абсолютных путей).
- В T-800 есть schema gate `scripts/t800_plugin_schema_gate.py`: сверяет манифест со схемой `registry/plugin.manifest.schema.json`, проверяет наличие `name` и что относительные пути `rules|skills|agents|commands|hooks` существуют на диске.

## Частые ошибки

- Несуществующие пути в `rules`/`skills`/`agents`/`commands`/`hooks` — gate и публикационный чеклист их отклоняют
- Абсолютные пути или `..` в манифесте — запрещены чеклистом публикации
- `version` не в формате semver — официальный reference описывает поле как Semantic version (`1.0.0`)
- Нет `name` — это единственное обязательное поле, без него манифест невалиден

## Источники

source: https://cursor.com/docs/plugins
source: https://cursor.com/docs/reference/plugins
