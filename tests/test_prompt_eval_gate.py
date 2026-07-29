#!/usr/bin/env python3
"""Тест prompt-eval gate на живом plugin_root.

  python3 tests/test_prompt_eval_gate.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "t800_prompt_eval_gate.py"
CASES = ROOT / "tests" / "fixtures" / "prompt-eval" / "cases.json"


def main() -> int:
    if not GATE.is_file():
        print("FAIL: нет scripts/t800_prompt_eval_gate.py", file=sys.stderr)
        return 1
    if not CASES.is_file():
        print("FAIL: нет tests/fixtures/prompt-eval/cases.json", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [sys.executable, str(GATE), "--plugin-root", str(ROOT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        print("FAIL: t800_prompt_eval_gate.py exit != 0", file=sys.stderr)
        return 1

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("FAIL: gate не вернул JSON", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        return 1

    if data.get("ok") is not True:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("FAIL: JSON ok != true", file=sys.stderr)
        return 1

    cases = data.get("cases") or []
    if len(cases) < 3:
        print(f"FAIL: ожидалось ≥3 кейса, got {len(cases)}", file=sys.stderr)
        return 1

    ids = {c.get("id") for c in cases if isinstance(c, dict)}
    required = {
        "factory_bypass_rule",
        "loop_conductor_open_only",
        "intake_clarifier_no_websearch",
    }
    missing_ids = required - ids
    if missing_ids:
        print(f"FAIL: нет кейсов {sorted(missing_ids)}", file=sys.stderr)
        return 1

    print("PASS test_prompt_eval_gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
