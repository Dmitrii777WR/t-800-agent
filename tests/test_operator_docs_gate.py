#!/usr/bin/env python3
"""Тест operator-docs gate на живом plugin_root.

  python3 tests/test_operator_docs_gate.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "t800_operator_docs_gate.py"

REQUIRED_RELS = [
    "shared/operator-surface-2026-07-contract.md",
    "docs/НАЧАЛО-РАБОТЫ.md",
    "docs/ПОЛНАЯ-ИНСТРУКЦИЯ.md",
    "playbooks/06-side-chat-i-async.md",
]


def main() -> int:
    if not GATE.is_file():
        print("FAIL: нет scripts/t800_operator_docs_gate.py", file=sys.stderr)
        return 1

    for rel in REQUIRED_RELS:
        if not (ROOT / rel).is_file():
            print(f"FAIL: нет {rel}", file=sys.stderr)
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
        print("FAIL: t800_operator_docs_gate.py exit != 0", file=sys.stderr)
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

    files = data.get("files") or []
    if len(files) < 4:
        print(f"FAIL: ожидалось ≥4 файла, got {len(files)}", file=sys.stderr)
        return 1

    checked = {f.get("file") for f in files if isinstance(f, dict)}
    missing = set(REQUIRED_RELS) - checked
    if missing:
        print(f"FAIL: gate не проверил {sorted(missing)}", file=sys.stderr)
        return 1

    operator = ROOT / "agents" / "t-800-operator.md"
    text = operator.read_text(encoding="utf-8")
    if "readonly: true" not in text:
        print("FAIL: t-800-operator должен остаться readonly: true", file=sys.stderr)
        return 1

    print("PASS test_operator_docs_gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
