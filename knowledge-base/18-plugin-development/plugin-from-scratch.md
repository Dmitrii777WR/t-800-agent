---
title: "Плагин с нуля: scaffold → install → packaging"
audience: advanced
tier: 4
last_synced: 2026-07-30
provenance: manual
author: t-800
source: https://cursor.com/docs/plugins
---

# Плагин с нуля: scaffold → install → packaging

## Простыми словами

Плагин Cursor — это папка с манифестом `.cursor-plugin/plugin.json` и компонентами (rules, skills, agents, commands, hooks, MCP-серверы). Цикл простой: scaffold папок → локальная проверка → публикация через Git-репозиторий.

## Шаг 1. Scaffold структуры

Создайте каталог по образцу из официального reference или начните с шаблона `github.com/cursor/plugin-template`:

```text
my-plugin/
├── .cursor-plugin/
│   └── plugin.json        # обязательный манифест
├── rules/
│   └── coding-standards.mdc
├── skills/
│   └── code-reviewer/
│       └── SKILL.md
├── agents/
│   └── security-reviewer.md
├── commands/
│   └── deploy.md
├── hooks/
│   └── hooks.json
├── mcp.json               # опционально: MCP-серверы
└── README.md
```

Все папки, кроме `.cursor-plugin/`, опциональны — берите только нужные. Если пути не прописаны в манифесте, Cursor находит компоненты в этих папках автоматически.

## Шаг 2. Заполните plugin.json

Минимум — поле `name`. Разбор полей и валидации: [plugin.json — манифест плагина](plugin-json-manifest.md).

## Шаг 3. Локальная установка

1. Создайте папку `~/.cursor/plugins/local/my-plugin`
2. Скопируйте туда файлы плагина — `.cursor-plugin/plugin.json` должен оказаться в корне папки плагина
3. Перезапустите Cursor или выполните **Developer: Reload Window**

Для быстрой итерации используйте symlink вместо копии:

```bash
ln -s <workspace>/my-plugin ~/.cursor/plugins/local/my-plugin
```

## Шаг 4. Проверка

- Убедитесь, что компоненты загрузились: rules, skills, MCP-серверы видны в Cursor
- Откройте **Customize** в сайдбаре — там управляются установленные плагины, MCP-серверы, rules и skills; skill вызывается вручную как `/skill-name` в чате

## Шаг 5. Packaging и публикация

Перед пушем в публичный git прочитайте [Git-гигиена публичного репо](public-repo-git-hygiene.md): личные пути и email из истории удаляются тяжело.

1. Запушьте плагин в **публичный** Git-репозиторий (логотип — коммитом в репо, опционально, но рекомендовано)
2. Отправьте ссылку на репозиторий на [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish)
3. Каждый плагин проходит ручное ревью команды Cursor; все плагины в marketplace обязаны быть open source
4. Несколько плагинов в одном репо — манифест маркетплейса `.cursor-plugin/marketplace.json` в корне репозитория

Командная раздача без публичного marketplace — **Team marketplaces** (Teams: 1 маркетплейс, Enterprise: без лимита): **Dashboard → Plugins → Add Marketplace**, режимы установки Default Off / Default On / Required.

Чеклист публикации из официального reference: валидный манифест, `name` уникальный kebab-case, frontmatter у всех компонентов, пути относительные и существующие, плагин протестирован локально.

## Источники

source: https://cursor.com/docs/plugins
source: https://cursor.com/docs/reference/plugins
source: https://cursor.com/docs/customize-cursor
