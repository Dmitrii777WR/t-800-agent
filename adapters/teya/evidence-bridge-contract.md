# Evidence Bridge Contract (Phase 2)

**Adapter version:** 2.0.0  
**Handoff schema:** [schemas/factory-handoff.schema.json](schemas/factory-handoff.schema.json)

## Paths

| Artifact | Path |
|----------|------|
| Factory handoff | `{memory}/factory-handoffs/<run-id>.json` |
| Provenance record | `{memory}/orchestration/provenance/<run-id>.json` |
| Rollout metadata link | `{memory}/orchestration/rollout/<command>.json` → `factory_provenance` only |
| Release evidence | handoff.`release_evidence` + `{memory}/orchestration/release-evidence.json` |

## Writers

| Field / action | T-800 | Teya verifier | Teya release tool | Materializer HITL |
|----------------|-------|---------------|-------------------|-------------------|
| `provenance_status=incomplete` | yes | — | — | — |
| `provenance_status=verified` | **no** | yes | — | — |
| `provenance_status=stale/revoked` | **no** | stale check | — | — |
| `status=released` / release_evidence | **no** | **no** | yes | **no** |
| `rollout_state` / success_streak | **no** | **no** | **no** | shadow stubs only |
| command-profile create | **no** | **no** | **no** | shadow + not_ready/onboarding_required |

## Invariants

1. Factory PASS / verified provenance ≠ runtime green / canary readiness.
2. Rollout link is metadata only (`factory_provenance`); never copies streak.
3. Secret scan + no personal absolute paths + no installed local writes.
4. Duplicate `run_id` with different brief against verified handoff → FAIL.
5. Stale provenance cannot be used as release evidence.

## Teya scripts

- `teya_t800_handoff_verify.py`
- `teya_t800_materialize_onboarding.py` (`--approve-materialization`)
- `teya_t800_provenance_stale_check.py`
- `teya_t800_release_evidence.py` (`TEYA_RELEASE_EVIDENCE_WRITER=1`)
