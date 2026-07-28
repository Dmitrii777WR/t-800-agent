"""Phase 2 evidence bridge helpers (hashes, secrets, provenance fields)."""

from __future__ import annotations

import hashlib
import json
import re
import secrets as secrets_mod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ADAPTER_VERSION = "2.0.0"
ONBOARDING_GATE_VERSION = "2.0.0"
PROVENANCE_STATUSES = frozenset({"incomplete", "verified", "stale", "revoked"})
T800_ALLOWED_PROVENANCE = frozenset({"incomplete"})
TEYA_ALLOWED_PROVENANCE = frozenset({"incomplete", "verified", "stale", "revoked"})

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_artifact_hashes(plugin_root: Path, rel_paths: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in rel_paths:
        p = Path(rel)
        if not p.is_absolute():
            p = plugin_root / rel
        digest = sha256_file(p)
        if digest:
            # store under relative key when possible
            try:
                key = str(p.resolve().relative_to(plugin_root.resolve())).replace("\\", "/")
            except ValueError:
                key = str(rel).replace("\\", "/")
            out[key] = digest
    return out


def scan_secrets(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(scan_secrets(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan_secrets(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        for pat in SECRET_PATTERNS:
            if pat.search(obj):
                hits.append(f"secret_pattern:{path}")
                break
    return hits


def empty_teya_entities() -> dict[str, list[str]]:
    return {
        "agents": [],
        "commands": [],
        "capabilities": [],
        "risks": [],
        "gates": [],
        "fixtures": [],
        "profiles": [],
    }


def build_phase2_fields(
    *,
    factory_run_id: str | None,
    factory_brief_id: str,
    source_commit: str | None = None,
    target_commit_before: str | None = None,
    target_commit_after: str | None = None,
    artifact_hashes: dict[str, str] | None = None,
    teya_entities: dict[str, list[str]] | None = None,
    release_status: str = "not_requested",
    rollout_link_status: str = "unlinked",
    provenance_status: str = "incomplete",
) -> dict[str, Any]:
    if provenance_status not in T800_ALLOWED_PROVENANCE:
        raise ValueError(
            f"T-800 may only set provenance_status={sorted(T800_ALLOWED_PROVENANCE)}; "
            f"got {provenance_status!r}"
        )
    entities = empty_teya_entities()
    if teya_entities:
        for key in entities:
            if key in teya_entities and isinstance(teya_entities[key], list):
                entities[key] = list(teya_entities[key])
    return {
        "factory_run_id": factory_run_id or "",
        "factory_brief_id": factory_brief_id,
        "source_commit": source_commit,
        "target_commit_before": target_commit_before,
        "target_commit_after": target_commit_after,
        "artifact_hashes": dict(artifact_hashes or {}),
        "adapter_version": ADAPTER_VERSION,
        "onboarding_gate_version": ONBOARDING_GATE_VERSION,
        "onboarding_gate_result": None,
        "onboarding_gate_evidence": None,
        "teya_entities": entities,
        "release_status": release_status,
        "rollout_link_status": rollout_link_status,
        "provenance_status": provenance_status,
        "release_evidence": None,
        "rollout_link": None,
    }


def factory_provenance_metadata(handoff: dict[str, Any], *, verified_at: str | None = None) -> dict[str, Any]:
    """Metadata-only block for Teya rollout artifacts (no streak / state)."""
    return {
        "factory_run_id": handoff.get("factory_run_id") or handoff.get("run_id"),
        "factory_brief_id": handoff.get("factory_brief_id"),
        "handoff_path": handoff.get("_handoff_path"),
        "provenance_status": handoff.get("provenance_status"),
        "verified_at": verified_at or handoff.get("verified_at"),
        "source_commit": handoff.get("source_commit"),
        "artifact_hashes": dict(handoff.get("artifact_hashes") or {}),
        "adapter_version": handoff.get("adapter_version") or ADAPTER_VERSION,
        "note": "metadata link only — not runtime green evidence",
    }


def assert_no_rollout_state_change(before: dict[str, Any] | None, after: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not before:
        return errors
    for key in ("success_streak", "rollout_state", "final_success_rate", "counts_toward_production_streak"):
        if key in before and after.get(key) != before.get(key):
            errors.append(f"forbidden_rollout_field_mutation:{key}")
    return errors


def nonce() -> str:
    return secrets_mod.token_hex(8)
