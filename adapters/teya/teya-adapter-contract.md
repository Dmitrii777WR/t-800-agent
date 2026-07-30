# Teya Adapter Contract (Phase 1+2)

**Pointer:** [`adapters/teya/README.md`](../adapters/teya/README.md) · Evidence: [`adapters/teya/evidence-bridge-contract.md`](../adapters/teya/evidence-bridge-contract.md)  
**Manifest:** [`adapters/teya/adapter.manifest.json`](../adapters/teya/adapter.manifest.json)

## Закон

1. T-800 generic core **не** знает внутренние registries Teya, кроме вызова adapter interface.
2. Adapter активируется только для `teya-plugin-dev` | `teya-client` | legacy `teya-pro`.
3. Post-factory handoff: `{memory}/factory-handoffs/<run-id>.json` — T-800 пишет только `factory_complete` | `onboarding_required` и `provenance_status=incomplete`.
4. `verified` / `released` — только Teya-side scripts (verifier / release evidence).
5. Onboarding check/gate + materializer — не меняют `rollout_state` выше shadow; не HITL promotion; не release sync.
6. Rollout link = metadata `factory_provenance` only (не streak / не runtime green).
7. Sibling `../TeyaPlugin` **не** canonical SoT; `~/.cursor/plugins/local/teya` — запрет записи.
8. Hook enforce не auto-enable; readiness via `t800_teya_hook_enforce_ready.py`.

## Scripts

| Side | Script |
|------|--------|
| T-800 | `t800_teya_write_handoff.py`, `t800_teya_onboarding_check.py`, `t800_teya_onboarding_gate.py`, `t800_teya_hook_enforce_ready.py` |
| Teya | `teya_t800_handoff_verify.py`, `teya_t800_materialize_onboarding.py`, `teya_t800_provenance_stale_check.py`, `teya_t800_release_evidence.py` |

## Live Teya contracts

Не копировать — читать из `$TEYA_PLUGIN_ROOT/shared/` (см. KB-15).
