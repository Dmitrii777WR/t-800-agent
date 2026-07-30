---
title: "Гайд по созданию субагентов"
source: https://cursor.com/ru/docs/subagents
audience: advanced
tier: 4
last_synced: 2026-07-30
provenance: manual
author: t-800
---

# Создание субагентов — полный гайд

## Где лежат файлы

| Область | Путь |
|---------|------|
| Проект | `.cursor/agents/имя.md` |
| Плагин (канон install) | `~/.cursor/plugins/local/t-800-agent/agents/имя.md` |
| User-home (опционально) | `~/.cursor/agents/имя.md` — **не** пишет `install-plugin` с 1.12.1 |
| Исходники плагина | `agents/имя.md` → rsync в `plugins/local/t-800-agent` |

При конфликте имён приоритет у проектных субагентов.

## Формат файла

```markdown
---
name: my-agent
description: >
  Одна чёткая зона ответственности. Use when ... Use proactively when ...
model: inherit
readonly: true
is_background: false
---

# Роль

Ты субагент `my-agent`, вызванный через Task(my-agent).

## Алгоритм
1. ...
2. ...

## Выход
Структурированный отчёт: что сделано, что передать следующему агенту.

## Запреты
- ...
```

## Поля frontmatter

| Поле | Обязательно | Default | Зачем |
|------|-------------|---------|-------|
| `name` | Нет | Из имени файла | ID для `Task(name)` и `/name`; lowercase + дефисы |
| `description` | Нет (но **критично**) | — | 1–3 предложения + триггеры; Agent решает по нему, делегировать ли |
| `model` | Нет | `inherit` | `inherit` = модель родителя; или конкретный ID модели |
| `readonly` | Нет | `false` | `true` = без правок файлов и state-changing shell |
| `is_background` | Нет | `false` | `true` = фоновый запуск без блокировки родителя |

### Параметры модели `[id=value]`

К ID модели можно дописать квадратные скобки с опциями через запятую:

| Пример | Поведение |
|--------|-----------|
| `composer-2.5[]` | Пустые скобки — базовый (не fast) вариант |
| `composer-2.5[fast=false]` | Стандартный вариант явно |
| `claude-opus-5[effort=high]` | Reasoning effort `high` |
| `claude-opus-5[context=300k]` | Окно контекста 300k |
| `claude-opus-5[effort=high,context=300k]` | Комбинация опций |

Доступные опции зависят от модели. Если модель заблокирована админом, недоступна на тарифе или требует Max Mode на legacy-плане — Cursor молча откатится на совместимую.

## Как вызывать

```text
Task(my-agent)
/ my-agent сделай X
Use the my-agent subagent to ...
```

Субагент **не видит** историю чата — родитель передаёт контекст в prompt.

## Subagent vs Skill vs Rule vs Command

| Артефакт | Когда |
|----------|-------|
| **Subagent** | Долгая задача, изоляция контекста, параллель, независимая проверка |
| **Skill** | Один повторяемый workflow, без отдельного контекста |
| **Rule** | Постоянные стандарты («всегда пиши по-русски») |
| **Command** | Явный slash-вызов сценария (`/t-800-factory`) |
| **Hook** | Реакция на событие (sessionStart, subagentStop, afterFileEdit) |

## Паттерны

### Verifier (проверка)
`readonly: true`, description: «Use after tasks marked done».

### Orchestrator (лид)
Координирует цепочку: architect → builder → integrator → auditor.

### Specialist (узкий эксперт)
Одна зона: «только SEO-мета», «только валидация registry».

## Антипаттерны (из официальной docs)

- Расплывчатые description («помогает с кодом»)
- Промпт на 2000+ слов
- 50+ агентов без категорий и роутинга
- Дублирование: subagent там, где хватит skill
- Skill вместо subagent для mentor-ролей с readonly

## Чеклист перед публикацией

- [ ] `name` уникален в реестре
- [ ] `description` содержит конкретные триггеры
- [ ] Промпт < 500 строк, структурирован
- [ ] `readonly` соответствует роли
- [ ] Запись в `registry/agents-registry.json`
- [ ] Строка в `docs/T-800-AGENTS.md`
- [ ] Routing rule обновлён (если нужна автоделегация)
- [ ] `scripts/validate-agents.ps1` проходит
- [ ] `scripts/audit-agent-graph.ps1` без ошибок

## Официальная ссылка

https://cursor.com/ru/docs/subagents
