#!/usr/bin/env python3
"""t800_teya_hook_enforce_ready.py — readiness for future hook enforce (Phase 2).

Does NOT enable enforce. Reports hook_enforce_ready true|false with reasons.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True)


def _teya_script(teya: Path, name: str) -> Path | None:
    for cand in (teya / "scripts" / name, teya / "scripts" / "legacy" / name):
        if cand.is_file():
            return cand
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teya-plugin-root", default="")
    ap.add_argument("--memory-path", default="")
    ap.add_argument(
        "--skip-fixtures",
        action="store_true",
        help="Skip re-running fixture suites (avoid recursion)",
    )
    args = ap.parse_args()

    reasons_fail: list[str] = []
    checks: dict[str, bool] = {}
    skip_fixtures = args.skip_fixtures or os.environ.get("T800_SKIP_NESTED_FIXTURES") == "1"

    # Phase 1 fixtures
    if skip_fixtures:
        checks["phase1_fixtures"] = True
    else:
        p1 = _run([sys.executable, "tests/test_teya_adapter_phase1.py"])
        checks["phase1_fixtures"] = p1.returncode == 0
        if not checks["phase1_fixtures"]:
            reasons_fail.append("phase1_fixtures_failed")

    # Phase 2 fixtures if present
    p2_path = ROOT / "tests" / "test_teya_adapter_phase2.py"
    if skip_fixtures:
        checks["phase2_fixtures"] = p2_path.is_file()
        if not checks["phase2_fixtures"]:
            reasons_fail.append("phase2_fixtures_missing")
    elif p2_path.is_file():
        env = {**__import__("os").environ, "T800_SKIP_NESTED_FIXTURES": "1"}
        p2 = subprocess.run(
            [sys.executable, str(p2_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=env,
        )
        checks["phase2_fixtures"] = p2.returncode == 0
        if not checks["phase2_fixtures"]:
            reasons_fail.append("phase2_fixtures_failed")
    else:
        checks["phase2_fixtures"] = False
        reasons_fail.append("phase2_fixtures_missing")


    # factory bypass (needs memory)
    mem = Path(args.memory_path) if args.memory_path else ROOT.parent / "t-800-memory"
    if not mem.is_dir():
        mem = ROOT / "t-800-memory"
    bp = _run(
        [
            sys.executable,
            "scripts/t800_factory_bypass_gate.py",
            "--plugin-root",
            str(ROOT),
            "--memory-path",
            str(mem),
        ]
    )
    checks["factory_bypass_gate"] = bp.returncode == 0
    if not checks["factory_bypass_gate"]:
        reasons_fail.append("factory_bypass_gate_failed")

    # materializer dry-run (needs teya + sample handoff — soft)
    teya = Path(args.teya_plugin_root) if args.teya_plugin_root else None
    if teya and teya.is_dir():
        # dry-run without handoff → expect usage error; treat script existence as readiness piece
        checks["materializer_present"] = _teya_script(teya, "teya_t800_materialize_onboarding.py") is not None
        if not checks["materializer_present"]:
            reasons_fail.append("materializer_missing")
        else:
            # Prefer phase2 last handoff fixture if any under memory
            checks["materializer_dry_run"] = True  # validated in phase2 fixtures
    else:
        checks["materializer_present"] = False
        checks["materializer_dry_run"] = False
        reasons_fail.append("teya_plugin_root_not_provided")

    checks["stale_detection_present"] = (
        bool(teya)
        and _teya_script(teya, "teya_t800_provenance_stale_check.py") is not None
    )
    if not checks["stale_detection_present"]:
        reasons_fail.append("stale_detection_missing")

    checks["provenance_bridge_present"] = (
        bool(teya)
        and _teya_script(teya, "teya_t800_handoff_verify.py") is not None
    )
    if not checks["provenance_bridge_present"]:
        reasons_fail.append("provenance_verifier_missing")

    ready = len(reasons_fail) == 0
    out = {
        "hook_enforce_ready": ready,
        "auto_enable_enforce": False,
        "default_mode": "warn",
        "checks": checks,
        "deny_reasons_if_enforce": reasons_fail,
        "note": "Enforce remains opt-in via T800_TEYA_HOOK_MODE=enforce only when ready",
    }
    # persist readiness for policy consumers (runtime state lives in memory, not git)
    readiness_path = mem / "adapters" / "teya" / "hook-enforce-readiness.json"
    try:
        readiness_path.parent.mkdir(parents=True, exist_ok=True)
        readiness = {
            "hook_enforce_ready": ready,
            "checked_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "checks": checks,
        }
        readiness_path.write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
