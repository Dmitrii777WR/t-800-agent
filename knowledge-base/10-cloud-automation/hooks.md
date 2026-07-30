---
title: "Hooks — реакции Cursor на события"
source: https://cursor.com/docs/hooks
audience: advanced
tier: 3
last_synced: 2026-07-30
provenance: manual
author: t-800
---

# Hooks — реакции Cursor на события

## Простыми словами

Hooks — это скрипты «когда случилось X, выполни Y»: Cursor запускает их на этапах работы агента — перед командой в терминале, после правки файла, при старте сессии. Скрипт получает JSON на stdin и отвечает JSON в stdout, поэтому hook может наблюдать, блокировать или менять поведение агента.

## 21 событие в 3 категориях

| Категория | Событие | Когда срабатывает |
|-----------|---------|-------------------|
| **Agent** | `sessionStart` | Новая сессия composer (fire-and-forget: env + контекст) |
| **Agent** | `sessionEnd` | Завершение сессии (логирование, cleanup) |
| **Agent** | `preToolUse` | Перед любым вызовом инструмента (все типы) |
| **Agent** | `postToolUse` | После успешного вызова инструмента |
| **Agent** | `postToolUseFailure` | Инструмент упал: ошибка, таймаут или deny |
| **Agent** | `subagentStart` | Перед запуском субагента (Task tool) |
| **Agent** | `subagentStop` | Субагент завершился, упал или отменён |
| **Agent** | `beforeShellExecution` | Перед shell-командой |
| **Agent** | `afterShellExecution` | После shell-команды (аудит вывода) |
| **Agent** | `beforeMCPExecution` | Перед вызовом MCP-инструмента |
| **Agent** | `afterMCPExecution` | После вызова MCP-инструмента |
| **Agent** | `beforeReadFile` | Перед чтением файла агентом (access control) |
| **Agent** | `afterFileEdit` | После правки файла агентом (форматтеры, учёт) |
| **Agent** | `beforeSubmitPrompt` | После «отправить», до запроса к backend |
| **Agent** | `preCompact` | Перед компакцией контекста (только наблюдение) |
| **Agent** | `stop` | Конец цикла агента (можно auto-followup) |
| **Agent** | `afterAgentResponse` | Агент закончил assistant-сообщение |
| **Agent** | `afterAgentThought` | Агент закончил thinking-блок |
| **Tab** | `beforeTabFileRead` | Tab (inline-дополнения) читает файл |
| **Tab** | `afterTabFileEdit` | Tab отредактировал файл (range/old_line/new_line) |
| **App lifecycle** | `workspaceOpen` | Cursor открыл workspace и при каждой смене папок; вне любой сессии агента |

## Типы исполнения

| Тип | Как работает |
|-----|--------------|
| `command` (default) | Shell-скрипт: JSON → stdin, JSON ← stdout. Exit `0` — ок (читать JSON-вывод), exit `2` — блок (равносильно `permission: "deny"`), прочие коды — hook упал, действие пропускается (fail-open) |
| `prompt` | LLM оценивает условие на естественном языке. Ответ `{ ok: boolean, reason?: string }`; `$ARGUMENTS` в промпте заменяется на JSON ввода (если placeholder нет — ввод дописывается в конец); опциональное поле `model` меняет модель оценки |

## Источники и приоритеты

Приоритет (высший → низший): **Enterprise → Team → Project → User**. Все подходящие hooks из всех источников запускаются; при конфликте ответов побеждает более приоритетный источник.

| Источник | Путь | cwd скриптов |
|----------|------|--------------|
| Enterprise (MDM) | macOS: `/Library/Application Support/Cursor/hooks.json`, Linux/WSL: `/etc/cursor/hooks.json`, Windows: `C:\ProgramData\Cursor\hooks.json` | Каталог enterprise-конфига |
| Team (Enterprise, cloud) | Веб-дашборд, синк каждые 30 минут | Managed-каталог hooks |
| Project | `<workspace>/.cursor/hooks.json` | Корень проекта |
| User | `~/.cursor/hooks.json` | `~/.cursor/` |

Формат файла — верхнеуровневый объект:

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      { "command": ".cursor/hooks/validate.sh", "matcher": "Shell|Write" }
    ]
  }
}
```

Для project hooks путь — от корня проекта (`.cursor/hooks/script.sh`, не `./hooks/script.sh`). Cursor следит за `hooks.json` и перечитывает при сохранении (auto-reload); если не подхватил — перезапуск Cursor.

## Опции отдельного скрипта

| Опция | Тип | Default | Зачем |
|-------|-----|---------|-------|
| `command` | string | **required** | Путь к скрипту или shell-команда |
| `type` | `command` / `prompt` | `command` | Тип исполнения |
| `timeout` | number | platform default | Таймаут в секундах |
| `loop_limit` | number / null | `5` | Лимит auto-followup для `stop`/`subagentStop`; `null` — без лимита |
| `failClosed` | boolean | `false` | `true` = сбой hook (crash, timeout, битый JSON) блокирует действие; для security-critical |
| `matcher` | object | — | Фильтр, когда hook запускается |

## Matcher-механика

| Событие | С чем сравнивается matcher |
|---------|----------------------------|
| `preToolUse` / `postToolUse` / `postToolUseFailure` | Точное имя инструмента или regex: `Shell`, `Read`, `Write`, `Grep`, `Delete`, `Task`; MCP — формат `MCP:<tool_name>` |
| `subagentStart` / `subagentStop` | Тип субагента (`generalPurpose`, `explore`, `shell`, …) |
| `beforeShellExecution` / `afterShellExecution` | Строка shell-команды целиком |
| `beforeReadFile` | Тип инструмента: `TabRead`, `Read` |
| `afterFileEdit` | Тип инструмента: `TabWrite`, `Write` |
| `beforeSubmitPrompt` | Фикс-значение `UserPromptSubmit` |
| `stop` | Фикс-значение `Stop` |
| `afterAgentResponse` | Фикс-значение `AgentResponse` |
| `afterAgentThought` | Фикс-значение `AgentThought` |

## Ключевые события детально

Все hooks получают базовые поля: `conversation_id`, `generation_id`, `model` (+ `model_id`, `model_params`), `hook_event_name`, `cursor_version`, `workspace_roots`, `user_email`, `transcript_path`.

- **`preToolUse`** — вход: `tool_name`, `tool_input`, `tool_use_id`, `cwd`. Ответ: `permission: allow | deny` (`ask` принят схемой, но сейчас не enforced), `user_message`, `agent_message`, `updated_input` — подменённый ввод инструмента.
- **`postToolUse`** — вход добавляет `tool_output` (JSON-строка результата) и `duration` (мс). Ответ: `additional_context` — контекст, который вставится в диалог после результата; `updated_mcp_tool_output` — только для MCP, заменяет вывод, который увидит модель.
- **`postToolUseFailure`** — вход: `error_message`, `failure_type: error | timeout | permission_denied`, `duration`, `is_interrupt`. Выходных полей пока нет.
- **`subagentStart`** — вход: `subagent_id`, `subagent_type`, `task`, `subagent_model`, `is_parallel_worker`. Ответ: `allow | deny`; `ask` не поддерживается и трактуется как `deny`.
- **`subagentStop` / `stop`** — loop-режим: ответ `followup_message` автоматически отправляется как следующее сообщение. У `subagentStop` followup потребляется только при `status: "completed"`. Поле `loop_count` показывает, сколько followup уже было (старт с 0); общий лимит — `loop_limit` скрипта (default 5).
- **`sessionStart`** — fire-and-forget: цикл агента не ждёт и не блокируется. Ответ: `env` — env-переменные на сессию (доступны всем последующим hooks этой сессии), `additional_context` — контекст в начало диалога. Поля `continue`/`user_message` схема принимает, но вызывающий код их не применяет.
- **`workspaceOpen`** — вход без `conversation_id`/`generation_id`/`model`/`transcript_path` (вне сессии). Ответ: `pluginPaths` — абсолютные пути к плагинам, которые Cursor подгрузит для этого workspace. Пропускается, если в окне ноль папок.

## Hooks в cloud agents

Cloud agents подхватывают `hooks.json` из корня репозитория и (на Enterprise) team/enterprise hooks. Работают 14 событий: `beforeShellExecution`, `afterShellExecution`, `beforeReadFile`, `afterFileEdit`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`, `subagentStop`, `beforeSubmitPrompt`, `preCompact`, `afterAgentResponse`, `afterAgentThought`, `stop`.

| Недоступно в cloud | Причина |
|--------------------|---------|
| `sessionStart` | Cloud-агент может стартовать в read-only окружении, hooks там не грузятся — событие сработало бы слишком поздно |
| `sessionEnd` | Нет границы «сессии редактора»: событие привязано к IDE-сессии, не к cloud-чату |
| `beforeMCPExecution` / `afterMCPExecution` | Отложено: read-only старт + неопределённый тайминг MCP hooks |
| `beforeTabFileRead` / `afterTabFileEdit` | Tab — фича IDE, в cloud не работает |
| `workspaceOpen` | IDE-lifecycle событие, к cloud не применимо |

Ограничения cloud: user-level hooks (`~/.cursor/hooks.json`) недоступны (у VM нет вашего home); только `command`-hooks (для `prompt`-hooks нет auth-обвязки в cloud); ранние read-only ходы идут без hooks — они включаются, когда окружение становится записываемым.

## Env-переменные для скриптов

| Переменная | Когда есть |
|------------|------------|
| `CURSOR_PROJECT_DIR` | Всегда — корень workspace |
| `CURSOR_VERSION` | Всегда |
| `CURSOR_USER_EMAIL` | Если пользователь залогинен |
| `CURSOR_TRANSCRIPT_PATH` | Если transcripts включены |
| `CURSOR_CODE_REMOTE` | `"true"` в remote workspace |
| `CLAUDE_PROJECT_DIR` | Всегда — алиас project dir (совместимость с Claude Code) |

Плюс env из ответа `sessionStart` — передаётся всем hooks этой сессии.

## Безопасность и troubleshooting

- `failClosed: true` — для security-critical hooks (рекомендовано для `beforeMCPExecution`); иначе сбой hook молча пропускает действие (fail-open).
- Нет удаления без backup, нет секретов в hook-файлах — команда hook должна быть понятна всей команде проекта.
- Проверка, что hooks активны: вкладка **Hooks** в **Customize** + output-канал **Hooks** (ошибки исполнения).
- Не работают? Проверьте относительные пути (project — от корня проекта, user — от `~/.cursor/`) и перезапустите Cursor.
- Exit code `2` блокирует действие — поведение как у Claude Code, для совместимости.

## Официальная ссылка

https://cursor.com/docs/hooks
