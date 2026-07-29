# Operator Surface Contract (2026-07)

Разделение поверхностей Cursor для оператора T-800: main chat, Side chat (`/side`), Slack agent, async Task / Build in Parallel.

## Поверхности

| Surface | Назначение | Что делать | Чего не делать |
|---------|------------|------------|----------------|
| **Main chat** | Factory / pipeline / `/t800-start` / `/t800-fix` | Сборка артефактов, gates, STATE | Длинная «разведка ради разведки» без цели |
| **Side chat** (`/side`) | Разведка, уточнения, чтение docs | Вопросы, Ask/Plan, короткие уточнения | Писать agents/skills/rules/hooks; обходить factory |
| **Slack agent** | Уведомления / запросы из Slack | **Plan then run** — сначала план, потом старт | Сразу Run Everything без плана |
| **Async / Parallel** | Fan-out research и независимые Task | `Build in Parallel`, async Task для specialists | Параллелить conflicting writes в одни файлы |

## Законы

1. **Main = конвейер.** Создание/правка Cursor-артефактов — только через T-800 factory (`/t800-start` / `/t800-fix`).
2. **Side (`/side`) = разведка.** Уточнения и чтение; результаты вернуть в main, не собирать артефакты в side.
3. **Slack = plan-before-start.** Сначала краткий план (что трогаем / что не трогаем), затем run.
4. **Async Task ok** для research fan-out и независимых readonly Task; не для conflicting PATCH одних `files[]`.

## Маркеры (docs gate)

В контракте, docs и playbook должны встречаться маркеры: `/side`, `Slack`, и `Parallel` **или** `async` (или фраза `Build in Parallel`).

Gate: `scripts/t800_operator_docs_gate.py`.

## Связано

- `playbooks/06-side-chat-i-async.md`
- `docs/НАЧАЛО-РАБОТЫ.md`
- `docs/ПОЛНАЯ-ИНСТРУКЦИЯ.md`
- `agents/t-800-operator.md` (readonly mentor)

## Версия

- Введён: 2026-07-29 · T-800 **1.21.4**
