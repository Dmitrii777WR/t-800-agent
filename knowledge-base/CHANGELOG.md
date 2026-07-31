---
title: "Changelog базы знаний T-800"
provenance: manual
author: t-800
---

# Changelog базы знаний T-800

Формат: дата — что изменилось — источник.

## 2026-07-31 — Релиз 1.23.0: глобальный аудит и закалка плагина

Итог глобального аудита (4 волны исправлений, 0 CRITICAL на выходе):

- **Публичность**: история git переписана (filter-repo) — удалены личный путь и email владельца из всех коммитов; единый автор `t-800-agent@users.noreply.github.com`; финальный скан секретов/личных данных по tracked-файлам — чисто
- **Целостность машинерии**: мёртвый хук `beforeFileEdit` заменён на реальный `preToolUse` (matcher Write|StrReplace|EditNotebook) — правки артефактов вне factory теперь реально блокируются; снят UTF-8 BOM в `knowledge-base/manifest.json` (чинит fail-closed kb-provenance); `t800_factory_bypass_gate.py` привязан к diff (время + покрытие файлов), +тест
- **Универсальность**: ядро product-agnostic — Teya вынесена в `adapters/teya/` (brain-агент, KB-15, 4 скрипта, шаблон, контракт; 16 git mv с сохранением истории) и declarative `profiles/teya-*.md`; rg-гейт ядра — 5 pointer-файлов
- **База знаний**: новый раздел `18-plugin-development/` (plugin.json-манифест, плагин с нуля/packaging, git-гигиена публичных репо, Cursor Router); 49 raw-снапшотов первоисточников (fetch 2026-07-30); hooks.md переработан (21 событие, preToolUse-эталон, release playbook); `manifest.json`: `last_full_sync`, sha256 страниц
- **Гигиена**: кросс-платформа (+2 ps1: discover-target-project, command-chains gate), `requirements-dev.txt`, pytest 27/27 (phase2 legacy-tolerant), registry F4 (system-auditor → system), INSTALL по факту без хардкода версий, −4 legacy ps1, runtime timestamps вне git

Гейты релиза: `run_gate --strict-create` PASS · `plugin_audit` PASS (42 агента, orphans=0) · schema PASS · kb provenance PASS · pytest 27/27 · sh -n 21 · py_compile 46 · frontmatter 74.

## 2026-07-31 — Волна 4: hygiene release (без bump версии)

- INSTALL.md по факту: версия — указатель на `.cursor-plugin/plugin.json`, 42 субагента · 18 команд, секция тестов (`requirements-dev.txt` + pytest), Windows-notes (hooks bash-only, ps1-пары)
- Единый источник версии: docs без хардкода версий (НАЧАЛО-РАБОТЫ, ПОЛНАЯ-ИНСТРУКЦИЯ, T-800-AGENTS, СЦЕНАРИЙ-СТАРТА, README badges 42/18)
- Runtime timestamps вне git: `adapters/teya/policy.json` очищен от `hook_enforce_ready*` (persist → `{memory}/adapters/teya/hook-enforce-readiness.json`), COVERAGE-REPORT без строки `**Generated:**`, audit-coverage.sh/.ps1 без datetime
- Кросс-платформа: +`discover-target-project.ps1` (pwsh parity .sh), +`t800_command_chains_gate.ps1`; −4 legacy ps1 (sync-docs, register-agent, fix-kb-frontmatter, test-dialogues); hooks `hooks/*.sh` — bash-only (Git Bash/WSL)
- Templates/registry: skill.md.template — `disable-model-invocation` по умолчанию выкл., factory-brief.template — flat YAML, command.md.template — stub-указатель; registry notes про description, `t-800-system-auditor` → category `system`; phase2-тесты legacy-tolerant (`scripts/legacy/` fallback); `requirements-dev.txt`

## 2026-07-31 — Волна 3: база знаний (без bump версии)

- Новый раздел `18-plugin-development/` (5 файлов): plugin.json-манифест, плагин с нуля (scaffold→install→packaging), git-гигиена публичных репо, Cursor Router + INDEX
- `02-agent-i-rezhimy/side-chats-and-search.md` — side chats (/side, /btw), conversation search
- Drift-обновления по cursor.com: hooks.md (21 событие, matcher, cloud-матрица), subagents.md (is_background, model-параметры, cloud), pricing (Router/пулы/Token Rate), agents-window.md, hooks-and-scripts.md (+гайд scripts), agent-vs-skill-vs-command.md (+commands how-to)
- `raw/` восстановлен: 49 .md-снапшотов первоисточников (fetch 2026-07-30); manifest.json — 8 новых URL, `last_full_sync: 2026-07-30`
- INDEX.md: +разделы 17 и 18

## 1.22.1 — 2026-07-29 (PATCH: hook enforce + golden 1.22)

- **Hook:** `factory_in_manifest` allow только `in_progress|running|started|active` (не `completed|ok|done`) — sibling `t-800-memory` с factory completed больше не обходит enforce; bypass `T800_FACTORY_RUN_ID` сохранён
- **Golden:** `docs/examples/self-golden/expected.json` — paths 1.22 (usage_ingest, auto_low, HITL, hook, contracts/templates/tests) + hashes
- **Tests:** `tests/test_hook_enforce_default.py` — isolated deny без sibling memory
- Version bump `.cursor-plugin/plugin.json` → **1.22.1**

## 1.22.0 — 2026-07-29 (Strengthen: usage ingest + auto-LOW HITL + hook enforce)

- **Usage ingest:** `scripts/t800_usage_ingest.py` + `templates/usage-draft.json.template`; merge env/file/CLI → telemetry `event=usage_ingest` `source=ui_or_env`; секция в `shared/telemetry-kpi-contract.md`
- **Auto-LOW HITL:** `auto_low.enabled=false` в `templates/loop-policy.json.template`; `t800_loop_hitl_approve.py` / `t800_auto_low_batch.py` (default dry-run; `--apply` → packs only, never factory); `shared/auto-low-hitl-contract.md`; `/t800-loop` §3b
- **Hook:** `hooks/before-artifact-edit.sh` default **enforce**; opt-out `T800_HOOK_MODE` / `T800_TEYA_HOOK_MODE`=warn|observe; Teya `adapters/teya/policy.json` — note only (`auto_enable_enforce` остаётся false, `default_mode` warn)
- Tests: `test_usage_ingest.py`, `test_auto_low_hitl.py`, `test_hook_enforce_default.py` + fixtures `tests/fixtures/auto-low/`
- Docs: `T800-SYSTEM-MAP.md`, `docs/ПОЛНАЯ-ИНСТРУКЦИЯ.md`; `verify-install.sh` / `.ps1`
- Version bump `.cursor-plugin/plugin.json` → **1.22.0**

## 1.21.5 — 2026-07-29 (Docs hygiene SYSTEM-MAP KPI)

- **`T800-SYSTEM-MAP.md`**: header/version **1.21.5**; источники CHANGELOG 1.12–1.21.4 (+ hygiene); KPI row CLOSED/partial (schema 1.21.1); telemetry вывод + App K без «полного KPI ещё нет»; registry note → текущая версия / roster 43; Teya vs T-800 **1.21.5**
- **`shared/plugin-audit-contract.md`**: footer → 2026-07-29 · T-800 **1.21.5**
- Version bump `.cursor-plugin/plugin.json` → **1.21.5**

## 1.21.4 — 2026-07-29 (Side chat / Slack / async docs)

- **`shared/operator-surface-2026-07-contract.md`**: main = factory; `/side` = разведка; Slack = plan-before-start; async/`Build in Parallel` для research fan-out
- Docs: `docs/НАЧАЛО-РАБОТЫ.md`, `docs/ПОЛНАЯ-ИНСТРУКЦИЯ.md` (§ Side / Slack / Parallel)
- Playbook: `playbooks/06-side-chat-i-async.md`
- Operator bullets (+ mirror `.cursor/agents/`); **readonly: true** сохранён
- Gate: `scripts/t800_operator_docs_gate.py` + `tests/test_operator_docs_gate.py` (маркеры `/side`, `Slack`, `Parallel|async`)
- `tests/TEST-SCENARIOS.md` сценарий 10; `verify-install.sh` / `.ps1`

## 1.21.3 — 2026-07-29 (Prompt eval gate)

- **`shared/prompt-eval-contract.md`**: Phase 4 behavioral eval — must_contain / must_not_contain для 3 поверхностей
- Fixtures: `tests/fixtures/prompt-eval/cases.json` (factory-bypass rule, loop-conductor open-only, intake no-WebSearch)
- Gate: `scripts/t800_prompt_eval_gate.py` (+ optional `--promptfoo` WARN skip) + `tests/test_prompt_eval_gate.py`
- `verify-install.sh` / `.ps1`: script + contract + run prompt-eval gate
- `skills/t-800-run-gates/references/gate-matrix.md`: строка prompt-eval
- Self-golden: `docs/examples/self-golden/expected.json` + hashes

## 1.21.2 — 2026-07-29 (Router cost policy)

- **`shared/router-cost-policy-contract.md`**: DEEP → Cost|Balance; factory architect/builder → Intelligence|Balance; `model: inherit` + Router Auto
- Skill note: `skills/t-800-run-gates/references/router-modes.md` + ссылка в `SKILL.md`
- `commands/t800-start.md` §2a Router; `agents/t-800-research-lead.md` DEEP Cost/Balance note (+ mirror)
- Gate: `scripts/t800_router_policy_gate.py` + `tests/test_router_policy_note.py`
- `verify-install.sh` / `.ps1`: script list + run router policy gate

## 1.21.1 — 2026-07-29 (KPI telemetry)

- **`scripts/t800_telemetry.py`**: schema **1.1** — optional `duration_ms` / `tokens_in` / `tokens_out` / `retries` (int≥0); CLI `--summarize` → `{memory}/telemetry/summary.json`; `--strict-kpi` (>50% без `duration_ms` → exit 1)
- Контракт: `shared/telemetry-kpi-contract.md`; ссылка в `shared/loop-engineering-contract.md`
- `t800_run_report.py`: optional `--duration-ms` / `--retries` (+ `--started-at`/`--ended-at` или env)
- Tests: `tests/test_telemetry_kpi.py` + fixture `tests/fixtures/telemetry/sample-runs.jsonl`

## 1.21.0 — 2026-07-29 (Cloud hooks matrix)

- **`shared/cloud-hooks-matrix.json`** + **`shared/cloud-hooks-matrix-contract.md`**: матрица Cursor 3.11 cloud conversation hooks (observe / gate_candidate / local_only, sole_gate_forbidden)
- **`scripts/t800_cloud_hooks_smoke.py`**: validate hooks.json — command-only, fail-open WARN на local_only, FAIL sole conversation gate / type=prompt; `--fixture-dir`
- Fixtures: `tests/fixtures/cloud-hooks/` + runner `tests/test_cloud_hooks_smoke.py`
- Example: `docs/examples/cloud-hub/hooks-observe.example.json`
- `shared/cloud-hub-setup-contract.md` § Cloud hooks matrix; `t-800-cloud-hub-smoke` checklist
- `verify-install.sh` / `.ps1`: наличие smoke script + matrix JSON

## 1.20.1 — 2026-07-29 (Hardening gates)

- **`t800_run_gate.py`**: `--require-kb-provenance`; auto-ON при `--strict-create` + `--plugin-root`: agents-mirror, kb-provenance, frontmatter-yaml, skill-frontmatter, plugin-schema, command-chains
- **`verify-install.sh` / `.ps1`**: запуск `t800_kb_provenance_gate.py` (hard-FAIL); ps1 — agents mirror gate run
- **`tests/test_teya_adapter_phase2.py`**: без TeyaPlugin → SKIP exit 0 + `phase2-last-run.json` status=skipped
- Docs: `/t800-loop` в НАЧАЛО-РАБОТЫ / ПОЛНАЯ-ИНСТРУКЦИЯ; plugin-sync / run-gates skills — prefer `--check`
- GitHub Release **v1.20.1** (закрывает gap релизов 1.18–1.20)

## 1.20.0 — 2026-07-28 (Teya Adapter Phase 1+2)

- **`adapters/teya/`** — отделение Teya-specific от generic core (manifest, profiles, discovery, handoff, checklist, policy, evidence bridge)
- Handoff schema **2.0.0**: provenance fields, artifact_hashes, teya_entities, provenance_status
- Scripts: `t800_teya_write_handoff.py`, `t800_teya_onboarding_check.py`, `t800_teya_onboarding_gate.py`, `t800_teya_hook_enforce_ready.py`
- brain-teya / integrator: profiles `teya-plugin-dev` / `teya-client` / legacy `teya-pro`; Teya только через adapter handoff
- discover: sibling `../TeyaPlugin` не canonical; installed local = readonly fallback
- hook: modes observe|warn|enforce (default warn); без hardcoded sibling memory path
- Rollout metadata link `factory_provenance` only (no streak/state); HITL materializer stubs only on Teya side
- Fixtures: `tests/test_teya_adapter_phase1.py` (28 PASS), `tests/test_teya_adapter_phase2.py` (21 PASS)
- Contract: `shared/teya-adapter-contract.md`
- **Не меняет** Teya `rollout_state` / release / HITL / production green

## 1.19.1 — 2026-07-24

- **P0 Surface+Sync+Gates:** skills 1→6 (factory-scaffold, fix-pack, plugin-sync slash-only, run-gates, command-chains + KB)
- `shared/command-chains.json` + `scripts/t800_command_chains_gate.py`
- `scripts/t800_plugin_sync.py` — CONTENT_DRIFT sha256 `--check` / `--apply` → MIR только `~/.cursor/plugins/local/t-800-agent`
- `scripts/t800_skill_frontmatter_gate.py` + `scripts/t800_plugin_schema_gate.py` + `registry/plugin.manifest.schema.json`
- **Wire:** `t800_run_gate.py` flags `--require-skill-frontmatter` / `--require-plugin-json-schema` / `--require-command-chains` (auto-ON при `--strict-create` + `--plugin-root`)
- `verify-install.sh` / `.ps1`: sync `--check` + новые gates; `install-plugin` — `t800_plugin_sync.py --apply` делегирует сюда
- `T800-SYSTEM-MAP.md` / plugin-audit-contract footer → **1.19.1**

## 1.19.0 — 2026-07-18

- **Discovery:** marker + `knowledge_vault_path` не перебивает `profile=teya-plugin-dev` на TeyaPlugin
- **Agents mirror gate:** `scripts/t800_agents_mirror_gate.py` — parity `agents/` ↔ `.cursor/agents/` (FS + git one-sided drift → FAIL)
- `verify-install.sh` — always-on mirror gate; `t800_run_gate.py --require-agents-mirror` (opt-in)

## 1.18.0 — 2026-07-18

- **Lesson Lifecycle v1.1** — `status`: open | applied | rejected (`shared/lesson-schema-contract.md`)
- `loop-queue`: секции **Open** / **Closed**; conductor — open-only approve
- `t800_lessons_to_fixpack.py`: generate только open+LOW; `--mark-applied` / `--mark-rejected`
- Fixtures: `tests/fixtures/loop/lifecycle/` + classifier ignore status-полей

## 1.17.1 — 2026-07-17

- **Target Knowledge Vault** — optional `knowledge_vault_path` в discovery/marker (runtime-only)
- Machine gate: `scripts/t800_kb_provenance_gate.py` (manifest pages[] или YAML frontmatter provenance: manual)
- Контракты: runtime-only forbid в `shared/project-memory-contract.md` + инлайн в `shared/project-discovery-contract.md`
- Релизная гигиена acceptance: version bump + CHANGELOG (этот PATCH)

## 1.17.0 — 2026-07-17

- **Loop Engineering v2** — semi-manual закрытие прогона: report → lessons → queue handoff
- Команда **`/t800-loop`** + субагент `t-800-loop-conductor` (system-adjacent, readonly)
- Контракты: `shared/loop-engineering-contract.md` v2.0.0, `shared/lesson-schema-contract.md`
- Скрипты: `t800_run_report.py`, `t800_lessons_export.py`, `t800_telemetry.py`, `t800_risk_classifier.py`, `t800_lessons_to_fixpack.py`, `t800_golden_check.py`, `t800-loop-dispatcher.sh`, `t800_loop_queue_write.py`
- Память: `runs/`, `telemetry/`, `loop-queue.md`, `.loop-paused`, `golden/`, `loop/` (session-notice); fix-packs из lessons
- `risk_class` — только script classifier; без stop/followup; sessionStart остаётся **один** hook (dispatcher внутри bootstrap)
- Handoff: после `/t800-start` → `/t800-loop`; batch из queue → `/t800-fix`

## 1.16.1 — 2026-07-14

- Защита от обхода factory (анти-паттерн Zen Intel): Plan→Implement только через `/t800-start` / `/t800-fix`
- Контракт: `shared/plan-to-factory-handoff-contract.md`
- BLOCKER в `rules/t-800-mandatory-routing.mdc`: запрет Write/StrReplace артефактов Cursor вне factory
- Machine gates: `scripts/t800_factory_bypass_gate.py`, `t800_run_gate.py --strict-create`
- Hook `preToolUse` (matcher `Write|StrReplace|EditNotebook`) → `hooks/before-artifact-edit.sh` (v1: WARN, не hard-deny)
- Тест-сценарий 6 в `tests/TEST-SCENARIOS.md`

## 1.16.0 — 2026-07-13

- **Отдел Cloud Hub Automation Setup** (6 агентов): `t-800-cloud-hub-lead` + analyst / prompt / pack / smoke + `t-800-cursor-kb-curator`
- Команда **`/t800-cloud-hub`** (алиас `/t800-hub-setup`) — blank Hub + Client TZ-builder для Cursor Automations
- Контракты: `shared/cloud-hub-setup-contract.md`, `shared/project-memory-dual-write-contract.md`
- Rule: `rules/t-800-cloud-hub-routing.mdc` (не always-on)
- Примеры паттернов: `docs/examples/cloud-hub/` (EXAMPLE only, без секретов)
- README / инструкции обновлены; roster **42** Task-субагента

## 1.15.3 — 2026-07-12

- `HEALTH-REPORT.md`: убраны абсолютные пути машины автора (плагин для команды)
- `health-check.sh` / `health-check.ps1`: в отчёт пишут относительные/`~/...` пути, не `/Users/...`

## 1.15.2 — 2026-07-09

- Подробный README: возможности, все команды, сценарии, **примеры промптов** (audit Cursor, doctor, plugin-audit, start/fix)
- Docs: НАЧАЛО-РАБОТЫ, ПОЛНАЯ-ИНСТРУКЦИЯ, ОБНОВЛЕНИЕ, СЦЕНАРИЙ-СТАРТА — без «обновляй zip каждый раз»; акцент на `/t800-bootstrap` и автообновление
- Описание плагина: старт через `/t800-start`, не через ручной update

## 1.15.1 — 2026-07-09

- Версию с GitHub читаем через **API** (`Accept: application/vnd.github.raw+json`), не через CDN `raw.githubusercontent.com` (у raw бывает лаг после push)
- Fallback на raw с cache-buster, если API недоступен
- Исправлено: после релиза 1.15.0 auto-check мог видеть старую 1.14.0 и уходить в fail-open

## 1.15.0 — 2026-07-09

- **Автопроверка версии** на `sessionStart`: `t800-auto-version-check.sh` + hook JSON `additional_context`
- При новой версии на GitHub — автоустановка, затем Reload + продолжение задачи
- Контракт: `shared/auto-update-contract.md`; TTL-кэш 6ч; `T800_SKIP_AUTO_UPDATE=1`
- `/t800-update` — ручной fallback к автохуку

## 1.14.0 — 2026-07-09

- Публичный GitHub: https://github.com/Khar-AG/t-800-agent
- `scripts/t800-update-from-github.sh` — сравнение версий + автоустановка с `main`
- `/t800-update` переписан под GitHub (не только zip)
- `shared/release-channel.json` — канон канала обновлений
- README + обложка `assets/t800-cover.png` + LICENSE MIT

## 1.13.1 — 2026-07-09

- `t800_plugin_audit.py`: orphans = **нет в registry** (не «нет в command-chains»)
- `soft_unreferenced` — info без WARN (leaf brains/factory — норма)
- Smoke: self-audit T-800 → PASS при полной registry sync

## 1.13.0 — 2026-07-09

- **`/t800-fix`** + `shared/fix-pipeline-contract.md` + `templates/fix-pack.md.template` — PATCH по fix-pack (SKIP/LIGHT research)
- **`/t800-doctor`** + `scripts/t800_doctor.py` — scripts-only health
- **`scripts/t800_run_gate.py`** — канонический machine gate (STATE + optional validate/audit)
- **`scripts/t800_audit_to_fixpack.py`** — audit → `{memory}/fix-packs/<slug>.md`
- Handoff: plugin-audit / system-audit → fix-pack → `/t800-fix`
- Factory: `mode: PATCH`; loop-engineering ссылается на run_gate
- Roster **36** без новых leaf/research/brain агентов

## 1.12.1 — 2026-07-09

- **No user-home mirrors:** `install-plugin` пишет только в `~/.cursor/plugins/local/t-800-agent`
- Убрано копирование agents/commands/rules/skills в `~/.cursor/{agents,commands,rules,skills}`
- Optional allowlisted cleanup старых `t-800-*` зеркал в user-home (не трогает `t-800-mandatory-routing.mdc`)
- `verify-install` / `health-check` проверяют PLUGIN paths; global mandatory-routing = WARN
- KEEP: `install-global-routing-rule.sh` + `/t800-bootstrap` (consent)
- Docs/KB/README/SKILL/TEST синхронизированы с plugin-local каноном

## 1.12.0 — 2026-07-09

- **Loop engineering** (Habr / Osmani / Anthropic evaluator-optimizer) — без новых агентов
- `shared/loop-engineering-contract.md` — STATE.md, machine gates, repair budget 2, research mode test
- `templates/STATE.md.template` + `scripts/t800_loop_state.sh` (init/touch)
- `/t800-start` + `/t800-plugin-audit`: init/read STATE; «готово» только с machine evidence
- Factory: repair ≤2 → escalate; auditor отчёт `machine_gates` + `ralph_wiggum_risk`
- Roster **36** без изменений

## 1.11.0 — 2026-07-09

- **`/t800-plugin-audit`** + `t-800-plugin-auditor` — аудит одного плагина (inventory, graph, orphans, alwaysApply)
- `scripts/t800_plugin_audit.py` — machine SoT → `{memory_path}/audits/<run-id>/`
- Контракт: `shared/plugin-audit-contract.md` (не путать с `/t800-audit` и `/teya-run-audit`)
- MEMORY LAW: runtime-карта чужого плагина **не** в knowledge-base T-800
- Roster **35 → 36**; category `system`

## 1.10.1 — 2026-07-09

- Контракт отделов: `shared/department-orchestration-contract.md`
- Директор → только лиды; Research/Brains/Factory **авто** fan-out специалистов
- Progress-бар между отделами (5 этапов); без новых research/brain агентов
- Обновлены: t800-start, research-lead, brain-lead, factory, mandatory-routing

## 1.10.0 — 2026-07-09

- `/t800-audit` + `t-800-system-auditor` — интерактивный разбор rules/skills (alwaysApply, bloat)
- `scripts/audit-cursor-bloat.sh` — оценка «жира» контекста
- `/t800-update` + `docs/ОБНОВЛЕНИЕ.md` — промпт обновления со старых версий
- Roster **34 → 35**

## 1.9.0 — 2026-07-09

- Автономный поиск: `t-800-research-strategist` (куда искать) + `t-800-research-synthesizer` (лучший вариант)
- Контракт: `shared/search-strategy-contract.md`
- Roster **32 → 34**; research-lead: strategist → fan-out → synthesizer
- Пользователь не обязан перечислять сайты — отдел сам выбирает GitHub/Reddit/ClawHub/Context7/cookbooks

## 1.8.1 — 2026-07-09

- Vendor mastodons: **OpenAI Cookbook**, Claude prompting, Gemini strategies, **Perplexity**, Kie, Cursor
- `t-800-research-vendor-docs` → `idea_seeds[]`; DEEP multi-model → min 3 мастодонта
- `prompt-craft` потребляет idea_seeds; matrix + Perplexity

## 1.8.0 — 2026-07-09

- Roster **27 → 32**: `t-800-research-clawhub`, `t-800-research-repo-miner`, `t-800-research-vendor-docs`, `t-800-research-news`, `t-800-intake-clarifier`
- Контракты: `shared/deep-research-contract.md`, `shared/clawhub-research-contract.md`, `shared/vendor-docs-matrix.md`
- Research-lead **DEEP MODE** default + coverage_matrix FAIL incomplete
- `/t800-start`: step 0b intake-clarifier; fan-out ClawHub / repo-miner / vendor / news
- Context7: trigger any API/SDK/MCP name; deep budget ≤5 (LIGHT ≤3)
- Gaps D1–D7 CLOSED (см. `17-team-capability-audit/team-roster-gaps.md`)

## 1.7.0 — 2026-07-09

- Roster **21 → 27**: `t-800-research-docs`, `t-800-prompt-craft`, `t-800-artifact-hooks`, `t-800-artifact-scripts`, `t-800-mcp-wiring`, `t-800-prompt-auditor`
- Контракты: `shared/research-docs-contract.md`, `shared/prompt-craft-contract.md`
- Цепочка `/t800-start`: scout → research-lead (+docs если library) → prompt-craft? → brain → factory (companions → prompt-auditor → auditor)
- Context7 **не** always-on; hooks.json → object map `{version, hooks:{event:[...]}}`
- Gaps G1–G7 CLOSED (см. `17-team-capability-audit/team-roster-gaps.md`)

## 2026-07-08 — v1.6.0 docs: сценарий старта 4 шага

- `docs/СЦЕНАРИЙ-СТАРТА.md` — канонический онбординг через Cursor Agent
- Обновлены README, INSTALL, НАЧАЛО-РАБОТЫ, share/T-800-ИНСТРУКЦИЯ.md

## 2026-07-08 — v1.6.0 First-run bootstrap + точность исполнения

- Команда `/t800-bootstrap` — аудит → объяснение → глобальное rule **по согласию**
- Скрипты: `first-run-status.sh`, `t800-state.sh`, `install-global-routing-rule.sh`
- `~/.t800/state.json` — флаг первого запуска
- Глобальное `t-800-mandatory-routing.mdc` **не** копируется при install — только bootstrap
- Контракты: `first-run-contract.md`, `execution-quality-contract.md`

## 2026-07-08 — v1.5.0 Onboard для новичков

- Команда `/t800-onboard` + агент `t-800-onboard`
- Скрипт `audit-cursor-setup.sh` — global vs local inventory

## 2026-07-06 — v1.4.0 Universal department + web research

- 20 агентов: research-lead, research-github, research-community
- artifact_surface: cursor-plugin | cursor-workspace | cursor-user
- research-freshness-contract (90 дней), GitHub/Reddit/Habr/X
- Цепочка: scout → research-lead → brain → factory

## 2026-07-06 — v1.3.0 Universal commands only

- Удалена `/t800-teya` — только `/t800-start` + текст задачи
- `list-target-plugins.sh`, `~/.t800/known-plugins.json`, `target-selection-contract.md`
- Выбор плагина: текст пользователя или один уточняющий вопрос

## 2026-07-06 — v1.2.0 Universal Project Memory

- Discovery: `discover-target-project.sh`, `init-project-memory.sh`
- Контракты: `project-discovery-contract.md`, `project-memory-contract.md`
- KB 16-universal-project-memory, аудит Teya memory
- Factory/brain/rules: memory_path из discovery, без hardcode target_plugin=t-800-agent
- `project-memory.marker.json` в workspace T-800 AGENT

## 2026-07-06 — v1.1.0 Department Hardening

- P0: verify-install, install.ps1/sh parity, docs/T-800-AGENTS, t800-start
- Bash gates: verify, validate, audit-graph, coverage, health
- Контракты: task-prompt, agent-quality, work-report, target-plugin-profiles
- Teya profile: KB 15-teya-pro-plugin, t-800-brain-teya, /t800-teya
- KB coverage 44/44 explicit (manifest-coverage-map)
- hooks.json эталон, t-800-memory/, factory example teya-test-scout-readonly

## 2026-07-02 (6)

- Добавлены `scripts/health-check.ps1` и команда `/t-800-health`
- Добавлены тестовые диалоги `tests/t-800-operator-dialogues.md` и `scripts/test-dialogues.ps1`
- Добавлена матрица маршрутизации `routing-test-cases.md`
- Добавлены учебные материалы `learning-path-7-days.md` и `typical-beginner-failures.md`
- Обновлены install/verify, INDEX и prompt `t-800-operator`

## 2026-07-02 (5)

- Добавлен maintainer-субагент `t-800-maintainer` для обслуживания KB, sync, coverage и verify
- Добавлен `scripts/audit-coverage.ps1` и отчёт `knowledge-base/COVERAGE-REPORT.md`
- Добавлены профили новичков и wizard-сценарии: первый проект, автоматизация, MCP, ошибка, Canvas
- Обновлены `agents/t-800-operator.md`, `INDEX.md`, `install-plugin.ps1`, `verify-install.ps1`, команды и rule обновления KB

## 2026-07-02 (4)

- Расширена база знаний до почти полной карты Cursor Docs/Help/Learn для T-800 Agent
- Добавлены P0-карточки: Ask Mode, Plan Mode, Debug Mode, Prompting, Agent Review, Terminal, Browser, Search, Security Run Modes
- Добавлены продвинутые разделы: Cloud Agents, Automations, Hooks, Teams/Dashboard, Pricing/Usage, Integrations, Bugbot/Security Agents, CLI, SDK, Cloud Agents API
- Обновлены `INDEX.md`, `agents/t-800-operator.md` и seed URL в `sync-docs.ps1`

## 2026-07-02 (3)

- Исправлена архитектура T-800 Agent: `t-800-operator` теперь полноценный субагент в `agents/t-800-operator.md`, а не skill-заглушка
- Удалён конфликтующий skill `t-800-operator`; оставлен только maintainer-skill `t-800-knowledge-base` с `disable-model-invocation: true`
- Добавлен `scripts/verify-install.ps1` для проверки установки
- Очищен `UPDATE-QUEUE.md` от mojibake и уже обработанных пунктов
- `sync-docs.ps1` переведён на ASCII-служебные строки, чтобы PowerShell 5 не портил кириллицу
- Sync проверен: 11/11 страниц OK, `docs/rules` закрыт существующей карточкой `03-kontekst/rules.md`

## 2026-07-02 (2)

- Добавлена карточка `02-agent-i-rezhimy/canvas-i-shared-canvases.md` (Canvas, Shared Canvases, Publish)
- Seed sync: `https://cursor.com/docs/agent/tools/canvas`
- Обновлены INDEX, glossarium, SKILL routing

## 2026-07-02

- Первая версия базы знаний (разделы 01–08, glossarium, playbooks)
- Добавлен `sync-docs.ps1` и контракт обновления
- Добавлено rule `t-800-knowledge-refresh`
