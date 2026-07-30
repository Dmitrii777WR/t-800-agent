# T-800 — контракт памяти целевого проекта

Память — **у каждого плагина/проекта своя**. T-800 отдел только **находит** её и **пишет** артефакты прогона, не подменяя нативную систему целевого плагина.

## Эталон: `{slug}-memory` (generic)

Каноничная память плагина живёт в двух слоях:

| Слой | Папка | Где | Горизонт |
|------|-------|-----|----------|
| Клиентский проект | `{slug}-memory/` (из профиля) | workspace клиента | Весь цикл проекта/фиксов |
| Разработка плагина | `plugin-memory/` | checkout плагина | Межсессионный handoff, roadmap, лог |
| Один прогон | `run-manifest.json` | memory профиля | Одна команда |

Типовые артефакты памяти (нативные имена — у целевого плагина свои):

- `run-manifest.json` — шаги Task, verdict
- `fragments/<agent>.md` — один файл на агента за этап
- `work-reports/` — развёрнутые отчёты
- handoff-файл склейки оркестратором
- режим/intake проекта по конвенциям плагина

**Вывод для T-800:** при работе на плагин с нативной памятью не создавать параллельную `t-800-memory/` в клиенте — писать в **нативную** память профиля (discovery `memory_path`). Эталонный аудит нативной памяти поставляет адаптер (см. `adapters/<id>/knowledge/`).

## Что пишет конвейер T-800 в memory_path

| Артефакт | Путь | Когда |
|----------|------|-------|
| **STATE прогона** | `{memory}/STATE.md` | Init в начале `/t800-start` / `/t800-plugin-audit`; touch после отделов |
| Бриф factory | `{memory}/factory-briefs/<slug>.yaml` | Старт factory |
| Manifest прогона | `{memory}/run-manifest.json` | Каждый `/t800-start` |
| Fragment этапа | `{memory}/fragments/t-800-<agent>.md` | После каждого Task factory |
| Audit отдела | `{memory}/audits/t-800-<topic>.md` | По запросу (readonly study) |
| Fix-pack | `{memory}/fix-packs/<slug>.md` | `/t800-fix`; из audit или lessons (`t800_lessons_to_fixpack.py`) |
| Run reports | `{memory}/runs/` | `/t800-loop` → `t800_run_report.py` |
| Telemetry | `{memory}/telemetry/` | `/t800-loop` → `t800_telemetry.py` |
| Loop queue | `{memory}/loop-queue.md` | Handoff lessons → fix; `t800_loop_queue_write.py` |
| Loop pause | `{memory}/.loop-paused` | Dispatcher skip (touch/rm) |
| Golden | `{memory}/golden/` | Self-golden / classifier fixtures cache |
| Session notice | `{memory}/loop/` | Notice для sessionStart (dispatcher) |

Шаблон STATE: `templates/STATE.md.template`. Скрипт: `scripts/t800_loop_state.sh`. Контракт: `shared/loop-engineering-contract.md` (+ `shared/lesson-schema-contract.md`).

Префикс `t-800-` в fragments — **маркер отдела**, не целевого плагина. Целевой плагин сохраняет свои нативные имена агентов и артефактов.

## Структура memory (минимум для нового плагина)

```text
{memory_dir}/
├── STATE.md           # loop: Last run / In progress / Gates
├── run-manifest.json
├── factory-briefs/
├── fix-packs/         # PATCH + lessons→fixpack
├── fragments/
├── audits/            # опционально
├── runs/              # Loop Engineering v2 reports
├── telemetry/         # loop metrics
├── loop/              # session-notice
├── golden/            # classifier / self-golden
├── loop-queue.md      # handoff queue
├── .loop-paused       # optional pause flag
└── README.md          # создаёт init-project-memory.sh
```

## Чтение перед Task

1. `{memory}/STATE.md` — blockers, lessons, last gates (обязательно)
2. `{memory}/run-manifest.json` — что уже делали
3. `{memory}/factory-briefs/*.yaml` — активные брифы
4. Нативные артефакты целевого плагина по профилю адаптера (mode/intake файлы, handoff/лог разработки — см. `adapters/<id>/`)

## profile → memory (канон)

| profile | memory_dir | plugin_root |
|---------|------------|-------------|
| declared adapter profile | `memory_dir` из `profiles/<id>.md` | из поля `plugin_root` профиля (env / workspace self) |
| `generic-plugin` | marker или `{slug}-memory/` | marker или workspace |
| `self-t800` | `t-800-memory/` | `t-800-agent/` |

## Если memory отсутствует

```bash
bash scripts/init-project-memory.sh --workspace "<ROOT>" --slug "<slug>"
```

Или спросить оператора: «Создать папку памяти `{slug}-memory/` для этого плагина?»

## Optional: knowledge_vault_path (marker / policy)

| Поле | Назначение |
|------|------------|
| `knowledge_vault_path` | **Optional.** Absolute path **или** relative от workspace root → Obsidian-style vault целевого проекта (frontmatter-заметки: learnings, proposals, canon). |

- В marker/policy: optional; отсутствует или `null` → discovery emit `null`.
- Relative → resolve к absolute от workspace root; absolute → как есть.

**Норма — Target vault runtime-only.** Читать можно: brain-lead, research (LIGHT), loop-conductor, factory architect.  
**Запрещено:** копировать содержимое vault в `agents/`, `skills/`, `knowledge-base/`, `shared/`, `commands/` плагина.  
Цитаты и выжимки живут только в `{memory}` целевого проекта (`brief_for_factory`, fragments, loop-queue).

## Cloud Hub artifacts

Подпапка **`cloud-hub/`** живёт **внутри** канонического `memory_dir` профиля (таблица выше не меняется).

Типичные файлы:

| Файл | Назначение |
|------|------------|
| `hub-instructions.md` | Thin blank Hub Instructions |
| `client-instructions.md` | Client TZ-builder Instructions |
| `pack-schema.json` | Department schema Client→Hub |
| `smoke-report.md` | Чеклист готовности |
| `capability-map.md` | Карта умений checkout |

Правила dual-write по профилю (куда писать, запрет duplicate roots, запрет client secrets в GitHub KB):  
**`shared/project-memory-dual-write-contract.md`**.

Закон **client native-first** сохраняется: cloud-hub данные клиента — в `<memory_dir>/cloud-hub/` профиля, **без** параллельной `t-800-memory/` в клиентском workspace.

Операционный закон Hub+Client: `shared/cloud-hub-setup-contract.md`. Команда: `/t800-cloud-hub`.

## Контракты адаптера (живое чтение)

При declared adapter profile читать живые контракты из plugin_root целевого плагина
(указатели — `adapters/<id>/adapter.manifest.json` → `live_contract_pointers`).

Knowledge адаптера: `adapters/<id>/knowledge/` (канонические пути, quality checklist, аудит памяти).
