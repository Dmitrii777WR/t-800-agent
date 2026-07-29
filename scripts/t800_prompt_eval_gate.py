#!/usr/bin/env python3
"""t800_prompt_eval_gate.py — узкий behavioral eval: must_contain / must_not_contain.

Usage:
  python3 scripts/t800_prompt_eval_gate.py --plugin-root .
  python3 scripts/t800_prompt_eval_gate.py --plugin-root . --cases PATH
  python3 scripts/t800_prompt_eval_gate.py --plugin-root . --promptfoo

Exit 0 = все кейсы PASS.
Exit 1 = FAIL (или битый fixture / нет файла).
--promptfoo: если CLI promptfoo нет → WARN skip (не FAIL); иначе делегирует (best-effort).
Без --promptfoo: только встроенный checker.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_CASES_REL = "tests/fixtures/prompt-eval/cases.json"


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def load_cases(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"не прочитать cases: {exc}") from exc

    if isinstance(raw, list):
        cases = raw
    elif isinstance(raw, dict):
        cases = raw.get("cases")
        if not isinstance(cases, list):
            raise ValueError("cases.json: нужен ключ cases[] или корневой массив")
    else:
        raise ValueError("cases.json: ожидается object или array")

    out: list[dict[str, Any]] = []
    for i, item in enumerate(cases):
        if not isinstance(item, dict):
            raise ValueError(f"cases[{i}]: не object")
        cid = str(item.get("id") or f"case_{i}")
        rel = str(item.get("file") or item.get("path") or "").strip()
        if not rel:
            raise ValueError(f"cases[{i}] ({cid}): нет file")
        must = item.get("must_contain") or []
        must_not = item.get("must_not_contain") or []
        if not isinstance(must, list) or not isinstance(must_not, list):
            raise ValueError(f"cases[{i}] ({cid}): must_* должны быть массивами строк")
        out.append(
            {
                "id": cid,
                "file": rel.replace("\\", "/"),
                "must_contain": [str(x) for x in must],
                "must_not_contain": [str(x) for x in must_not],
            }
        )
    return out


def eval_case(plugin_root: Path, case: dict[str, Any]) -> dict[str, Any]:
    rel = case["file"]
    path = plugin_root / rel
    result: dict[str, Any] = {
        "id": case["id"],
        "file": rel,
        "ok": False,
        "missing_contain": [],
        "forbidden_hits": [],
        "error": None,
    }
    if not path.is_file():
        result["error"] = f"нет файла {rel}"
        return result
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        result["error"] = f"не прочитать {rel}: {exc}"
        return result

    missing = [s for s in case["must_contain"] if s not in text]
    forbidden = [s for s in case["must_not_contain"] if s in text]
    result["missing_contain"] = missing
    result["forbidden_hits"] = forbidden
    result["ok"] = not missing and not forbidden
    return result


def try_promptfoo(plugin_root: Path, cases_path: Path) -> dict[str, Any]:
    """Optional promptfoo CLI. Missing → WARN skip, not FAIL."""
    exe = shutil.which("promptfoo")
    if not exe:
        _eprint("WARN promptfoo: CLI не найден — skip (не FAIL)")
        return {"requested": True, "skipped": True, "reason": "promptfoo_cli_missing"}

    # Best-effort: нет канонического promptfooconfig в репо — фиксируем наличие CLI.
    proc = subprocess.run(
        [exe, "--version"],
        cwd=str(plugin_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "requested": True,
        "skipped": False,
        "cli": exe,
        "version_exit": proc.returncode,
        "version_stdout": (proc.stdout or "").strip()[:200],
        "cases": str(cases_path),
        "note": "built-in checker — source of truth; promptfoo presence only",
    }


def run_gate(
    plugin_root: Path,
    cases_path: Path,
    *,
    use_promptfoo: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        cases = load_cases(cases_path)
    except ValueError as exc:
        summary = {
            "ok": False,
            "plugin_root": str(plugin_root.resolve()),
            "cases_path": str(cases_path),
            "cases": [],
            "failed": 1,
            "passed": 0,
            "errors": [str(exc)],
            "promptfoo": None,
        }
        return summary

    results = [eval_case(plugin_root, c) for c in cases]
    for r in results:
        if r.get("error"):
            errors.append(f"{r['id']}: {r['error']}")
            _eprint(f"FAIL prompt-eval {r['id']}: {r['error']}")
        elif not r["ok"]:
            parts: list[str] = []
            if r["missing_contain"]:
                parts.append(f"нет must_contain={r['missing_contain']}")
            if r["forbidden_hits"]:
                parts.append(f"есть must_not_contain={r['forbidden_hits']}")
            msg = "; ".join(parts) or "fail"
            errors.append(f"{r['id']}: {msg}")
            _eprint(f"FAIL prompt-eval {r['id']}: {msg}")

    promptfoo_info: dict[str, Any] | None = None
    if use_promptfoo:
        promptfoo_info = try_promptfoo(plugin_root, cases_path)

    passed = sum(1 for r in results if r.get("ok"))
    failed = len(results) - passed
    ok = failed == 0 and not errors
    return {
        "ok": ok,
        "plugin_root": str(plugin_root.resolve()),
        "cases_path": str(cases_path.resolve()),
        "cases": results,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "promptfoo": promptfoo_info,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T-800 prompt eval gate (must_contain / must_not_contain)"
    )
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=Path("."),
        help="Корень плагина (default: .)",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help=f"Путь к cases.json (default: {{plugin-root}}/{DEFAULT_CASES_REL})",
    )
    parser.add_argument(
        "--promptfoo",
        action="store_true",
        help="Опционально: проверить наличие promptfoo CLI (missing → WARN skip)",
    )
    args = parser.parse_args()
    root = args.plugin_root.resolve()
    if not root.is_dir():
        summary = {
            "ok": False,
            "plugin_root": str(root),
            "cases_path": None,
            "cases": [],
            "passed": 0,
            "failed": 1,
            "errors": [f"plugin-root не директория: {root}"],
            "promptfoo": None,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        _eprint(f"FAIL prompt-eval: plugin-root не директория: {root}")
        return 1

    cases_path = (
        args.cases.expanduser().resolve()
        if args.cases
        else (root / DEFAULT_CASES_REL).resolve()
    )
    if not cases_path.is_file():
        summary = {
            "ok": False,
            "plugin_root": str(root),
            "cases_path": str(cases_path),
            "cases": [],
            "passed": 0,
            "failed": 1,
            "errors": [f"нет cases: {cases_path}"],
            "promptfoo": None,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        _eprint(f"FAIL prompt-eval: нет cases {cases_path}")
        return 1

    summary = run_gate(root, cases_path, use_promptfoo=args.promptfoo)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
