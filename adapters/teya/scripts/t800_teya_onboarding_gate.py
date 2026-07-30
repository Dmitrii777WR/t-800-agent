#!/usr/bin/env python3
"""t800_teya_onboarding_gate.py — machine gate for Teya adapter boundary (Phase 1).

ALLOW only when Teya profile + handoff + registrations OK.
DENY generic-plugin through adapter, canary/enforced from T-800, installed local writes, etc.

Usage:
  python3 scripts/t800_teya_onboarding_gate.py \\
    --profile PROFILE --plugin-root PATH --memory-path PATH \\
    --handoff PATH [--require-teya]

Exit 0 = PASS (or skip if non-teya and --require-teya not set)
Exit 1 = DENY
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from adapters.teya.discovery import assert_not_sibling_canonical  # noqa: E402
from adapters.teya.handoff import (  # noqa: E402
    ALLOWED_T800_STATUSES,
    contains_personal_absolute_path,
    load_handoff,
    validate_handoff_for_t800_write,
)
from adapters.teya.profiles import is_teya_profile  # noqa: E402

import importlib.util

_check_path = Path(__file__).resolve().parent / "t800_teya_onboarding_check.py"
_spec = importlib.util.spec_from_file_location("t800_teya_onboarding_check", _check_path)
_check_mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_check_mod)
run_check = _check_mod.run_check


def fail(summary: dict[str, Any], msg: str) -> int:
    summary["ok"] = False
    summary["error"] = msg
    summary["verdict"] = "DENY"
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def pass_ok(summary: dict[str, Any], msg: str = "PASS") -> int:
    summary["ok"] = True
    summary["verdict"] = "ALLOW"
    summary["message"] = msg
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--plugin-root", required=True)
    ap.add_argument("--memory-path", required=True)
    ap.add_argument("--handoff", default="")
    ap.add_argument("--workspace", default="")
    ap.add_argument(
        "--require-teya",
        action="store_true",
        help="FAIL if profile is not Teya (adapter invoked wrongly)",
    )
    ap.add_argument(
        "--skip-non-teya",
        action="store_true",
        default=True,
        help="Exit 0 for non-teya when not --require-teya (default)",
    )
    args = ap.parse_args()

    profile = args.profile.strip()
    plugin_root = Path(args.plugin_root).resolve()
    memory_path = Path(args.memory_path).resolve()
    summary: dict[str, Any] = {
        "gate": "t800_teya_onboarding_gate",
        "profile": profile,
        "plugin_root": str(plugin_root),
        "memory_path": str(memory_path),
        "denies": [],
    }

    # Generic must not pass through Teya adapter when require-teya
    if not is_teya_profile(profile):
        if args.require_teya:
            return fail(summary, "adapter_invoked_for_non_teya_profile")
        return pass_ok(summary, "skip_non_teya_profile")

    if not args.handoff:
        return fail(summary, "factory_handoff_missing")

    handoff_path = Path(args.handoff)
    if not handoff_path.is_file():
        return fail(summary, f"factory_handoff_not_found:{handoff_path}")

    try:
        handoff = load_handoff(handoff_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return fail(summary, f"handoff_invalid:{exc}")

    summary["run_id"] = handoff.get("run_id")
    summary["handoff_status"] = handoff.get("status")

    # Status rules
    status = str(handoff.get("status") or "")
    if status == "released":
        # T-800 must not claim released without Teya evidence file
        evidence = memory_path / "orchestration" / "release-evidence.json"
        if not evidence.is_file():
            return fail(summary, "released_without_teya_release_evidence")
    if status not in ALLOWED_T800_STATUSES | {"onboarding_pass", "onboarding_blocked", "released"}:
        return fail(summary, f"unknown_handoff_status:{status}")

    write_check = validate_handoff_for_t800_write(
        {**handoff, "status": status if status in ALLOWED_T800_STATUSES else "onboarding_required"}
    )
    # If status is already onboarding_pass from external, don't re-apply t800 write rules for status
    if status in ALLOWED_T800_STATUSES and not write_check["ok"]:
        summary["denies"].extend(write_check["errors"])
        return fail(summary, "handoff_t800_write_rules_violated")

    # Forbid T-800 setting canary/enforced
    for key in ("rollout_state", "desired_rollout_state"):
        val = str(handoff.get(key) or "").lower()
        if val in {"canary", "enforced"}:
            return fail(summary, f"t800_attempted_{val}")

    if handoff.get("release_completed") is True and status != "released":
        return fail(summary, "release_claimed_without_released_status")

    # Installed local deny
    root_s = str(plugin_root).replace("\\", "/")
    if "/.cursor/plugins/local/teya" in root_s:
        return fail(summary, "artifact_outside_canonical_teya_git")

    handoff_root = str(handoff.get("target_plugin_root") or "").replace("\\", "/")
    if "/.cursor/plugins/local/teya" in handoff_root:
        return fail(summary, "handoff_targets_installed_local_teya")

    # Personal absolute paths in file lists
    for key in ("files_created", "files_modified", "expected_fixtures"):
        for item in handoff.get(key) or []:
            if contains_personal_absolute_path(str(item)):
                return fail(summary, f"personal_absolute_path_in_{key}")

    # Sibling not canonical when workspace provided
    if args.workspace:
        sib = assert_not_sibling_canonical(plugin_root, args.workspace)
        # Only deny if handoff claims canonical via sibling source
        if handoff.get("plugin_root_source") == "sibling" or (
            sib.get("is_sibling") and handoff.get("canonical_claim") is True
        ):
            return fail(summary, "sibling_path_used_as_canonical")

    # Artifact files must exist
    for rel in list(handoff.get("files_created") or []) + list(handoff.get("files_modified") or []):
        p = Path(rel)
        if not p.is_absolute():
            p = plugin_root / rel
        if not p.exists():
            summary["denies"].append(f"missing_artifact:{rel}")

    if summary["denies"] and any(d.startswith("missing_artifact:") for d in summary["denies"]):
        return fail(summary, "artifact_files_missing")

    # Run checklist
    check = run_check(
        plugin_root=plugin_root,
        memory_path=memory_path,
        handoff=handoff,
        profile=profile,
    )
    summary["checklist"] = {
        "ok": check.get("ok"),
        "verdict": check.get("verdict"),
        "errors": check.get("errors"),
    }
    if not check.get("ok"):
        summary["denies"].extend(check.get("errors") or [])
        return fail(summary, "onboarding_checklist_failed")

    # Provenance match
    if handoff.get("target_profile") and not is_teya_profile(str(handoff.get("target_profile"))):
        return fail(summary, "handoff_profile_not_teya")

    return pass_ok(summary, "teya_onboarding_gate_pass")


if __name__ == "__main__":
    # Allow `from scripts...` when run as file
    raise SystemExit(main())
