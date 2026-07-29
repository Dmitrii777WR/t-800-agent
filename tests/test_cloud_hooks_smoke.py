#!/usr/bin/env python3
"""Runner: cloud hooks smoke на fixtures. Exit 0 только если все ожидания ok-/bad- совпали.

  python3 tests/test_cloud_hooks_smoke.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts" / "t800_cloud_hooks_smoke.py"
FIXTURES = ROOT / "tests" / "fixtures" / "cloud-hooks"
MATRIX = ROOT / "shared" / "cloud-hooks-matrix.json"


def main() -> int:
    if not SMOKE.is_file():
        print("FAIL: нет scripts/t800_cloud_hooks_smoke.py", file=sys.stderr)
        return 1
    if not MATRIX.is_file():
        print("FAIL: нет shared/cloud-hooks-matrix.json", file=sys.stderr)
        return 1
    if not FIXTURES.is_dir():
        print("FAIL: нет tests/fixtures/cloud-hooks/", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [
            sys.executable,
            str(SMOKE),
            "--fixture-dir",
            str(FIXTURES),
            "--matrix",
            str(MATRIX),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)

    try:
        summary = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("FAIL: smoke не вернул JSON summary", file=sys.stderr)
        return 1

    ok = bool(summary.get("ok")) and proc.returncode == 0
    results = summary.get("results") or []
    for row in results:
        status = "PASS" if row.get("matched") else "FAIL"
        print(
            f"[{status}] {row.get('file')} "
            f"ok={row.get('ok')} expected_ok={row.get('expected_ok')}"
        )

    if not ok:
        print("FAIL cloud hooks smoke fixtures", file=sys.stderr)
        return 1

    print("OK cloud hooks smoke fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
