#!/usr/bin/env python3
"""CLI: write factory handoff for Teya adapter (status factory_complete|onboarding_required only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT))

from adapters.teya.handoff import build_handoff, write_handoff  # noqa: E402
from adapters.teya.profiles import is_teya_profile  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--memory-path", required=True)
    ap.add_argument("--handoff-json", required=True, help="Path to JSON payload (partial ok)")
    args = ap.parse_args()

    payload = json.loads(Path(args.handoff_json).read_text(encoding="utf-8"))
    profile = str(payload.get("target_profile") or "")
    if not is_teya_profile(profile):
        print(json.dumps({"ok": False, "error": "not_teya_profile", "profile": profile}, ensure_ascii=False))
        return 1

    handoff = build_handoff(
        run_id=str(payload["run_id"]),
        factory_brief_id=str(payload.get("factory_brief_id") or ""),
        target_profile=profile,
        target_plugin_root=str(payload.get("target_plugin_root") or ""),
        artifact_type=str(payload.get("artifact_type") or "bundle"),
        artifact_ids=list(payload.get("artifact_ids") or []),
        files_created=list(payload.get("files_created") or []),
        files_modified=list(payload.get("files_modified") or []),
        requested_capabilities=list(payload.get("requested_capabilities") or []),
        requested_risk_effects=list(payload.get("requested_risk_effects") or []),
        expected_commands=list(payload.get("expected_commands") or []),
        expected_agents=list(payload.get("expected_agents") or []),
        expected_gates=list(payload.get("expected_gates") or []),
        expected_fixtures=list(payload.get("expected_fixtures") or []),
        release_required=bool(payload.get("release_required", True)),
        release_command=str(payload.get("release_command") or "/teya-release-sync"),
        provenance=payload.get("provenance"),
        status=str(payload.get("status") or "onboarding_required"),
        factory_run_id=payload.get("factory_run_id"),
        source_commit=payload.get("source_commit"),
        target_commit_before=payload.get("target_commit_before"),
        target_commit_after=payload.get("target_commit_after"),
        artifact_hashes=payload.get("artifact_hashes"),
        teya_entities=payload.get("teya_entities"),
        provenance_status=str(payload.get("provenance_status") or "incomplete"),
    )
    # Pass through onboarding flags
    for key in (
        "department_required",
        "capability_required",
        "intent_required",
        "capability_registration_required",
        "risk_registration_required",
        "require_fixtures",
        "new_command_stub",
        "plugin_root_source",
        "canonical_claim",
        "onboarding_policy_hash",
        "profile_hashes",
        "require_gates",
        "gate_checklist_only",
    ):
        if key in payload:
            handoff[key] = payload[key]

    path = write_handoff(args.memory_path, handoff)
    print(json.dumps({"ok": True, "path": str(path), "status": handoff["status"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
