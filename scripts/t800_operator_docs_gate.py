#!/usr/bin/env python3
"""t800_operator_docs_gate.py — маркеры Side/Slack/Parallel в docs surface.

Проверяет, что в контракте, docs и playbook есть:
  - /side
  - Slack
  - Parallel ИЛИ async ИЛИ «Build in Parallel»

Usage:
  python3 scripts/t800_operator_docs_gate.py --plugin-root .

Exit 0 = PASS. Exit 1 = FAIL.
Stdout: JSON {ok, files, errors}.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FILES = [
    "shared/operator-surface-2026-07-contract.md",
    "docs/НАЧАЛО-РАБОТЫ.md",
    "docs/ПОЛНАЯ-ИНСТРУКЦИЯ.md",
    "playbooks/06-side-chat-i-async.md",
]

MARKER_SIDE = "/side"
MARKER_SLACK = "Slack"
PARALLEL_MARKERS = ("Build in Parallel", "Parallel", "async")


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def check_file(plugin_root: Path, rel: str) -> dict[str, Any]:
    path = plugin_root / rel
    result: dict[str, Any] = {
        "file": rel,
        "ok": False,
        "missing": [],
        "error": None,
    }
    if not path.is_file():
        result["error"] = f"нет файла {rel}"
        result["missing"] = [MARKER_SIDE, MARKER_SLACK, "Parallel|async"]
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        result["error"] = f"не прочитать {rel}: {exc}"
        return result

    missing: list[str] = []
    if MARKER_SIDE not in text:
        missing.append(MARKER_SIDE)
    if MARKER_SLACK not in text:
        missing.append(MARKER_SLACK)
    if not any(m in text for m in PARALLEL_MARKERS):
        missing.append("Parallel|async|Build in Parallel")

    result["missing"] = missing
    result["ok"] = not missing
    return result


def resolve_plugin_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"plugin-root не директория: {root}")
        return root
    cwd = Path.cwd().resolve()
    if (cwd / ".cursor-plugin" / "plugin.json").is_file():
        return cwd
    if (cwd / "scripts" / "t800_operator_docs_gate.py").is_file():
        return cwd
    raise FileNotFoundError("укажите --plugin-root")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operator docs markers gate")
    parser.add_argument("--plugin-root", default=None, help="Корень плагина t-800-agent")
    args = parser.parse_args(argv)

    try:
        plugin_root = resolve_plugin_root(args.plugin_root)
    except FileNotFoundError as exc:
        summary = {"ok": False, "files": [], "errors": [str(exc)]}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        _eprint(f"FAIL: {exc}")
        return 1

    files_out: list[dict[str, Any]] = []
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        item = check_file(plugin_root, rel)
        files_out.append(item)
        if item.get("error"):
            errors.append(f"{rel}: {item['error']}")
        elif not item.get("ok"):
            errors.append(f"{rel}: отсутствуют маркеры {item.get('missing')}")

    ok = not errors
    summary = {"ok": ok, "files": files_out, "errors": errors}
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not ok:
        for err in errors:
            _eprint(f"FAIL: {err}")
        _eprint("FAIL: t800_operator_docs_gate")
        return 1

    _eprint("PASS: t800_operator_docs_gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
