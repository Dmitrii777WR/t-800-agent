"""Factory handoff artifact for Teya onboarding (Phase 1+2 Evidence Bridge)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .evidence import (
    ADAPTER_VERSION,
    ONBOARDING_GATE_VERSION,
    PROVENANCE_STATUSES,
    T800_ALLOWED_PROVENANCE,
    build_phase2_fields,
    empty_teya_entities,
    scan_secrets,
    utc_now,
)

SCHEMA_VERSION = "2.0.0"

ALLOWED_T800_STATUSES = frozenset({"factory_complete", "onboarding_required"})
FORBIDDEN_T800_STATUSES = frozenset(
    {
        "released",
        "onboarding_pass",
        "canary",
        "enforced",
    }
)
ALL_STATUSES = frozenset(
    {
        "factory_complete",
        "onboarding_required",
        "onboarding_pass",
        "onboarding_blocked",
        "released",
    }
)

PERSONAL_ABS_RE = re.compile(
    r"^/(?:Users|home)/[^/]+/(?:Desktop|Documents|Downloads|Library)/",
    re.IGNORECASE,
)
INSTALLED_TEYA_FRAGMENT = "/.cursor/plugins/local/teya"


def build_handoff(
    *,
    run_id: str,
    factory_brief_id: str,
    target_profile: str,
    target_plugin_root: str,
    artifact_type: str,
    artifact_ids: list[str] | None = None,
    files_created: list[str] | None = None,
    files_modified: list[str] | None = None,
    requested_capabilities: list[str] | None = None,
    requested_risk_effects: list[str] | None = None,
    expected_commands: list[str] | None = None,
    expected_agents: list[str] | None = None,
    expected_gates: list[str] | None = None,
    expected_fixtures: list[str] | None = None,
    release_required: bool = True,
    release_command: str = "/teya-release-sync",
    provenance: dict[str, Any] | None = None,
    status: str = "onboarding_required",
    created_at: str | None = None,
    factory_run_id: str | None = None,
    source_commit: str | None = None,
    target_commit_before: str | None = None,
    target_commit_after: str | None = None,
    artifact_hashes: dict[str, str] | None = None,
    teya_entities: dict[str, list[str]] | None = None,
    provenance_status: str = "incomplete",
) -> dict[str, Any]:
    if status not in ALLOWED_T800_STATUSES:
        raise ValueError(
            f"T-800 may only set status in {sorted(ALLOWED_T800_STATUSES)}; got {status!r}"
        )
    if provenance_status not in T800_ALLOWED_PROVENANCE:
        raise ValueError(
            f"T-800 may only set provenance_status=incomplete; got {provenance_status!r}"
        )

    entities = empty_teya_entities()
    if teya_entities:
        for key in entities:
            if key in teya_entities:
                entities[key] = list(teya_entities[key] or [])
    # Auto-fill entities from expected_* when not provided
    if not entities["agents"] and expected_agents:
        entities["agents"] = list(expected_agents)
    if not entities["commands"] and expected_commands:
        entities["commands"] = list(expected_commands)
    if not entities["gates"] and expected_gates:
        entities["gates"] = list(expected_gates)
    if not entities["fixtures"] and expected_fixtures:
        entities["fixtures"] = list(expected_fixtures)
    if not entities["capabilities"] and requested_capabilities:
        entities["capabilities"] = [
            c
            for c in requested_capabilities
            if c not in {"department_required", "capability_required"}
        ]
    if not entities["risks"] and requested_risk_effects:
        entities["risks"] = list(requested_risk_effects)
    if not entities["profiles"] and expected_commands:
        entities["profiles"] = [
            (c if str(c).endswith(".json") else f"{str(c).lstrip('/')}.json")
            for c in expected_commands
        ]

    phase2 = build_phase2_fields(
        factory_run_id=factory_run_id or run_id,
        factory_brief_id=factory_brief_id,
        source_commit=source_commit,
        target_commit_before=target_commit_before,
        target_commit_after=target_commit_after,
        artifact_hashes=artifact_hashes,
        teya_entities=entities,
        provenance_status=provenance_status,
    )

    base = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "factory_brief_id": factory_brief_id,
        "created_at": created_at or utc_now(),
        "target_profile": target_profile,
        "target_plugin_root": target_plugin_root,
        "artifact_type": artifact_type,
        "artifact_ids": list(artifact_ids or []),
        "files_created": list(files_created or []),
        "files_modified": list(files_modified or []),
        "requested_capabilities": list(requested_capabilities or []),
        "requested_risk_effects": list(requested_risk_effects or []),
        "expected_commands": list(expected_commands or []),
        "expected_agents": list(expected_agents or []),
        "expected_gates": list(expected_gates or []),
        "expected_fixtures": list(expected_fixtures or []),
        "release_required": bool(release_required),
        "release_command": release_command,
        "provenance": provenance
        or {
            "writer": "t-800-factory",
            "adapter": "teya",
            "phase": 2,
            "adapter_version": ADAPTER_VERSION,
        },
        "status": status,
        "rollout_mutation": None,
    }
    base.update(phase2)
    return base


def contains_personal_absolute_path(value: str) -> bool:
    if not value:
        return False
    if INSTALLED_TEYA_FRAGMENT in value.replace("\\", "/"):
        return True
    if PERSONAL_ABS_RE.search(value.replace("\\", "/")):
        return True
    return False


def validate_handoff_for_t800_write(
    handoff: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate before T-800 writes handoff JSON. Does not mutate Teya rollout."""
    errors: list[str] = []
    status = str(handoff.get("status") or "")
    if status not in ALLOWED_T800_STATUSES:
        errors.append(f"forbidden_status_for_t800:{status}")
    if status in FORBIDDEN_T800_STATUSES or status == "released":
        errors.append(f"t800_cannot_set:{status}")

    prov = str(handoff.get("provenance_status") or "incomplete")
    if prov not in T800_ALLOWED_PROVENANCE:
        errors.append(f"t800_cannot_set_provenance_status:{prov}")

    # Forbid downgrade verified → incomplete without revoke
    if existing:
        prev = str(existing.get("provenance_status") or "")
        if prev == "verified" and prov == "incomplete":
            errors.append("cannot_downgrade_verified_to_incomplete_without_revoke")
        if prev == "verified" and handoff.get("artifact_hashes") != existing.get("artifact_hashes"):
            # T-800 rewriting hashes after verify
            errors.append("t800_cannot_mutate_verified_hashes")

    for key in ("files_created", "files_modified", "expected_fixtures"):
        for item in handoff.get(key) or []:
            s = str(item)
            if s.startswith("/") and contains_personal_absolute_path(s):
                errors.append(f"personal_absolute_path:{key}:{s}")
            if INSTALLED_TEYA_FRAGMENT in s.replace("\\", "/"):
                errors.append(f"installed_local_teya_path:{key}:{s}")

    root = str(handoff.get("target_plugin_root") or "")
    if INSTALLED_TEYA_FRAGMENT in root.replace("\\", "/"):
        errors.append("target_plugin_root_is_installed_local")

    if handoff.get("rollout_mutation") not in (None, {}, []):
        errors.append("t800_must_not_set_rollout_mutation")

    rollout = handoff.get("rollout_state")
    if rollout and str(rollout).lower() in {"canary", "enforced", "guarded"}:
        errors.append(f"t800_cannot_set_rollout_state:{rollout}")

    if handoff.get("release_completed") is True:
        errors.append("t800_cannot_mark_release_completed")
    if str(handoff.get("release_status") or "") == "released":
        errors.append("t800_cannot_set_release_status_released")

    # T-800 must not write Teya gate verification as verified
    if handoff.get("onboarding_gate_result") == "PASS" and prov == "verified":
        errors.append("t800_cannot_self_verify")

    # Must not write rollout artifact content
    if handoff.get("teya_rollout_artifact") is not None:
        errors.append("t800_cannot_write_teya_rollout_artifact")

    secret_hits = scan_secrets(handoff)
    if secret_hits:
        errors.extend(secret_hits)

    if handoff.get("adapter_version") and handoff.get("adapter_version") != ADAPTER_VERSION:
        # allow older incomplete handoffs being upgraded by writer setting current
        pass

    return {"ok": not errors, "errors": errors}


def handoff_path(memory_path: str | Path, run_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", run_id).strip("-") or "run"
    return Path(memory_path) / "factory-handoffs" / f"{safe}.json"


def write_handoff(memory_path: str | Path, handoff: dict[str, Any]) -> Path:
    path = handoff_path(memory_path, str(handoff["run_id"]))
    existing = None
    if path.is_file():
        try:
            existing = load_handoff(path)
        except (OSError, ValueError, json.JSONDecodeError):
            existing = None
        # Duplicate run_id with different factory_brief is forbidden unless same brief
        if existing and existing.get("factory_brief_id") != handoff.get("factory_brief_id"):
            if existing.get("provenance_status") in {"verified", "stale"}:
                raise ValueError("duplicate_run_id_conflict")

    check = validate_handoff_for_t800_write(handoff, existing=existing)
    if not check["ok"]:
        raise ValueError(f"handoff_validation_failed: {check['errors']}")

    # Ensure defaults
    handoff.setdefault("adapter_version", ADAPTER_VERSION)
    handoff.setdefault("onboarding_gate_version", ONBOARDING_GATE_VERSION)
    handoff.setdefault("provenance_status", "incomplete")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_handoff(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("handoff_not_object")
    return data


def apply_teya_verification(
    handoff: dict[str, Any],
    *,
    gate_result: str,
    gate_evidence: dict[str, Any],
    provenance_status: str,
    writer: str = "teya_t800_handoff_verify",
) -> dict[str, Any]:
    """Teya-side only: mutate handoff verification fields."""
    if provenance_status not in PROVENANCE_STATUSES:
        raise ValueError(f"invalid_provenance_status:{provenance_status}")
    if writer.startswith("t-800") or writer == "t-800-factory":
        raise ValueError("t800_cannot_apply_verification")
    out = dict(handoff)
    out["onboarding_gate_result"] = gate_result
    out["onboarding_gate_evidence"] = gate_evidence
    out["onboarding_gate_version"] = ONBOARDING_GATE_VERSION
    out["provenance_status"] = provenance_status
    out["verified_at"] = utc_now() if provenance_status == "verified" else out.get("verified_at")
    out["verified_by"] = writer
    if provenance_status == "verified" and out.get("status") == "onboarding_required":
        out["status"] = "onboarding_pass"
    if provenance_status in {"stale", "revoked"} and out.get("status") == "onboarding_pass":
        out["status"] = "onboarding_blocked"
    return out
