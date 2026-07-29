#!/usr/bin/env python3
"""t800_router_policy_gate.py — note-gate: Router Cost policy contract + skill ref.

Checks:
  1) shared/router-cost-policy-contract.md exists
  2) contract contains markers: Cost, Balance, Intelligence, DEEP, inherit
  3) skills/t-800-run-gates/references/router-modes.md exists

Usage:
  python3 scripts/t800_router_policy_gate.py --plugin-root .

Exit 0 = ok (JSON on stdout). Exit 1 = FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MARKERS = ("Cost", "Balance", "Intelligence", "DEEP", "inherit")
CONTRACT_REL = "shared/router-cost-policy-contract.md"
SKILL_REF_REL = "skills/t-800-run-gates/references/router-modes.md"


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def check_plugin(plugin_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    markers_hit: dict[str, bool] = {m: False for m in MARKERS}
    missing_markers: list[str] = []

    contract_path = plugin_root / CONTRACT_REL
    skill_ref_path = plugin_root / SKILL_REF_REL

    contract_ok = contract_path.is_file()
    skill_ok = skill_ref_path.is_file()

    if not contract_ok:
        errors.append(f"нет файла {CONTRACT_REL}")
        _eprint(f"FAIL router policy: нет {CONTRACT_REL}")
    else:
        try:
            text = contract_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"не прочитать {CONTRACT_REL}: {exc}")
            _eprint(f"FAIL router policy: не прочитать {CONTRACT_REL}: {exc}")
            text = ""
        for marker in MARKERS:
            found = marker in text
            markers_hit[marker] = found
            if not found:
                missing_markers.append(marker)
        if missing_markers:
            msg = f"в {CONTRACT_REL} нет маркеров: {', '.join(missing_markers)}"
            errors.append(msg)
            _eprint(f"FAIL router policy: {msg}")

    if not skill_ok:
        errors.append(f"нет файла {SKILL_REF_REL}")
        _eprint(f"FAIL router policy: нет {SKILL_REF_REL}")

    ok = contract_ok and skill_ok and not missing_markers and not errors
    # If only marker/read errors already in errors, ok is False via missing_markers
    if errors:
        ok = False

    return {
        "ok": ok,
        "plugin_root": str(plugin_root.resolve()),
        "contract": CONTRACT_REL if contract_ok else None,
        "skill_ref": SKILL_REF_REL if skill_ok else None,
        "markers": markers_hit,
        "missing_markers": missing_markers,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T-800 Router Cost policy note-gate (contract + markers + skill ref)"
    )
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=Path("."),
        help="Корень плагина (default: .)",
    )
    args = parser.parse_args()
    root = args.plugin_root.resolve()
    if not root.is_dir():
        _eprint(f"FAIL router policy: plugin-root не директория: {root}")
        summary = {
            "ok": False,
            "plugin_root": str(root),
            "contract": None,
            "skill_ref": None,
            "markers": {m: False for m in MARKERS},
            "missing_markers": list(MARKERS),
            "errors": [f"plugin-root не директория: {root}"],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1

    summary = check_plugin(root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
