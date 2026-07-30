---
title: "Teya Pro — карта раздела для T-800"
audience: advanced
tier: 5
last_synced: 2026-07-06
---

# Teya Pro Plugin — для конвейера T-800

T-800 — **generic factory**. Интеграция с Teya — только через **[`adapters/teya/`](../../adapters/teya/README.md)** (Phase 1).  
T-800 **не копирует** vault Teya и **не** владеет capability/risk/rollout. Живые контракты: `$TEYA_PLUGIN_ROOT/shared/`.

Profiles: `teya-plugin-dev` | `teya-client` | legacy `teya-pro`.  
Post-factory: `{memory}/factory-handoffs/<run-id>.json` → `t800_teya_onboarding_gate.py`.

## Документы

| Файл | Назначение |
|------|------------|
| [canonical-paths.md](canonical-paths.md) | TEYA_PLUGIN_ROOT, запрет local/teya |
| [agent-quality-checklist.md](agent-quality-checklist.md) | Минимум агента Teya |
| [task-prompt-7-parts.md](task-prompt-7-parts.md) | 7 частей Task-промпта |
| [plugin-release-handoff.md](plugin-release-handoff.md) | release-sync после правок (не из T-800) |
| [command-chains-map.md](command-chains-map.md) | teya_docs_build, COMMAND_AGENTS |
| [departments-and-stacks.md](departments-and-stacks.md) | manager vs leaf, отделы |
| `../../shared/teya-adapter-contract.md` | Граница adapter Phase 1 |

## Субагент

`Task(t-800-brain-teya)` — обязательно при profile teya-* (см. `adapters/teya/profiles.py`).

## Команда

**Закон:** нет project-specific slash-команд. Только `/t800-start` + «для Teya» в тексте или выбор из `~/.t800/known-plugins.json`.
