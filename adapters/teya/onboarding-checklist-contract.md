# Teya Adapter — Onboarding Checklist Contract (Phase 1)

**Статус:** machine-readable companion — `scripts/t800_teya_onboarding_check.py`  
**Gate:** `scripts/t800_teya_onboarding_gate.py`  
**Handoff:** `{memory}/factory-handoffs/<run-id>.json`

## Scope

Проверка **после** Factory CREATE/PATCH для profile `teya-plugin-dev` | `teya-client` | alias `teya-pro`.

Checklist **только читает**. Запрещено:

- менять `rollout_state`
- создавать green streak
- HITL promotion
- `/teya-release-sync`
- писать в `~/.cursor/plugins/local/teya`

## Agent

| Check | PASS if |
|-------|---------|
| file_exists | `agents/<id>.md` под canonical plugin_root |
| frontmatter_valid | YAML frontmatter парсится; есть `name` |
| department_membership | id в `shared/agent-departments.json` **или** handoff `requested_capabilities` помечен `department_required` |
| capability_mapping | agent→capability в registry **или** explicit `capability_required` в handoff |
| mirror_requirement | `.cursor/agents/<id>.md` существует, если плагин требует mirror |
| duplicate_conflict | нет второго файла с тем же `name` |

## Command

| Check | PASS if |
|-------|---------|
| command_file | `commands/teya-*.md` существует |
| command_chains | stem в `shared/command-chains.json` |
| intent_mapping | команда в `COMMAND_INTENT` (`scripts/teya_intent_router.py`) **или** handoff `intent_required` |
| command_profile | `shared/command-profiles/<stem>.json` |
| owner_caps_gates | profile содержит owner/manager или caps/gates |
| rollout_ceiling | `rollout_state` ∈ {absent, shadow, disabled} — **не** canary/enforced/guarded для нового stub |
| readiness_default | readiness `not_ready` \| `onboarding_required` \| absent |
| fixtures_listed | `expected_fixtures` / `expected_gates` в handoff не пусты при `artifact_type=command` |

## Capability / risk / gate

| Check | PASS if |
|-------|---------|
| registry_entry | id есть в соответствующем registry |
| rebuild_check | handoff provenance ссылается на check run **или** fixture отмечает rebuild |
| fixture_exists | путь из `expected_fixtures` |
| provenance_link | `factory_brief_id` + `run_id` совпадают с handoff |

## Live contracts (pointers only)

Читать из `$TEYA_PLUGIN_ROOT` (не копировать в T-800):

- `shared/agent-quality-contract.md`
- `shared/capability-registry-contract.md`
- `shared/risk-engine-contract.md`
- `shared/command-profile-contract.md` (если есть)

## Status transitions

| Writer | Allowed status |
|--------|----------------|
| T-800 Factory / adapter writer | `factory_complete`, `onboarding_required` |
| Onboarding gate (readonly verdict) | report `onboarding_pass` / `onboarding_blocked` **в stdout**, не обязан писать handoff |
| Teya release / human | `released` |

T-800 **никогда** не ставит `released`, `canary`, `enforced`.
