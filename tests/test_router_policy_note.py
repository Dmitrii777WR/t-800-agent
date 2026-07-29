#!/usr/bin/env python3
"""Тест note-gate Router Cost policy.

  python3 tests/test_router_policy_note.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "t800_router_policy_gate.py"


def main() -> int:
    if not GATE.is_file():
        print("FAIL: нет scripts/t800_router_policy_gate.py", file=sys.stderr)
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
        print("FAIL: t800_router_policy_gate.py exit != 0", file=sys.stderr)
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

    print("PASS test_router_policy_note")
    return 0


if __name__ == "__main__":
    sys.exit(main())
