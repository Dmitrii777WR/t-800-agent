#!/usr/bin/env python3
"""Smoke: validate hooks.json against shared/cloud-hooks-matrix.json.

Usage:
  python3 scripts/t800_cloud_hooks_smoke.py --hooks PATH [--matrix PATH]
  python3 scripts/t800_cloud_hooks_smoke.py --fixture-dir DIR
  python3 scripts/t800_cloud_hooks_smoke.py --hooks PATH --require-cloud-safe
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = PLUGIN_ROOT / "shared" / "cloud-hooks-matrix.json"

SOLE_GATE_EVENTS = frozenset(
    {"afterAgentResponse", "afterAgentThought", "stop", "beforeSubmitPrompt"}
)
COMPANION_GATES = frozenset({"beforeShellExecution", "subagentStart"})


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Не удалось прочитать JSON {path}: {exc}") from exc


def index_matrix(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    hooks = matrix.get("hooks")
    if not isinstance(hooks, list):
        raise ValueError("matrix.hooks должен быть массивом")
    out: dict[str, dict[str, Any]] = {}
    for item in hooks:
        if not isinstance(item, dict) or "name" not in item:
            raise ValueError("Каждый hook матрицы нужен с полем name")
        out[str(item["name"])] = item
    return out


def validate_hooks(
    data: Any,
    matrix_by_name: dict[str, dict[str, Any]],
    *,
    require_cloud_safe: bool = False,
    source: str = "hooks",
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "ok": False,
            "source": source,
            "errors": ["hooks.json должен быть object map"],
            "warnings": [],
        }

    if "version" not in data:
        errors.append("Отсутствует поле version")
    hooks_obj = data.get("hooks")
    if not isinstance(hooks_obj, dict):
        errors.append("Поле hooks должно быть object {event: [entries...]}")
        return {
            "ok": False,
            "source": source,
            "errors": errors,
            "warnings": warnings,
        }

    present_events = [str(k) for k in hooks_obj.keys()]
    has_companion = any(e in COMPANION_GATES for e in present_events)
    has_gate_candidate = False
    has_observe = False

    for event, entries in hooks_obj.items():
        event_name = str(event)
        meta_row = matrix_by_name.get(event_name)
        if not isinstance(entries, list):
            errors.append(f"{event_name}: значение должно быть массивом hook entries")
            continue

        if meta_row is None:
            warnings.append(f"{event_name}: нет в cloud-hooks-matrix (неизвестный event)")
        else:
            cloud_ok = bool(meta_row.get("cloud_supported"))
            role = str(meta_row.get("role") or "")
            if role == "gate_candidate" and entries:
                has_gate_candidate = True
            if role == "observe" and entries:
                has_observe = True
            if not cloud_ok and entries:
                msg = (
                    f"{event_name}: cloud_supported=false (local_only) — "
                    "ок локально, не cloud-safe"
                )
                if require_cloud_safe:
                    errors.append(msg + " (--require-cloud-safe)")
                else:
                    warnings.append(msg)

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"{event_name}[{idx}]: entry должен быть object")
                continue
            entry_type = entry.get("type")
            if entry_type == "prompt":
                errors.append(
                    f"{event_name}[{idx}]: type=prompt запрещён "
                    "(cloud/command-only policy)"
                )
            elif entry_type not in (None, "command"):
                # неизвестный type — не FAIL, но WARN
                warnings.append(
                    f"{event_name}[{idx}]: type={entry_type!r} не command "
                    "(ожидается command-based)"
                )
            if entry_type in (None, "command") and not entry.get("command"):
                # Cursor допускает command field; без command и без prompt — WARN
                if "prompt" in entry and entry_type != "prompt":
                    warnings.append(
                        f"{event_name}[{idx}]: есть prompt без type=prompt"
                    )
                elif not entry.get("command"):
                    warnings.append(
                        f"{event_name}[{idx}]: нет поля command"
                    )

    # Sole production gate policy
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    sole = meta.get("sole_production_gate")
    if sole:
        sole_name = None
        if isinstance(sole, bool) and sole:
            # boolean true: любой sole conversation gate claim
            claimed = [e for e in present_events if e in SOLE_GATE_EVENTS]
            if claimed and not has_companion:
                errors.append(
                    "meta.sole_production_gate=true без companion "
                    f"beforeShellExecution/subagentStart (events={claimed})"
                )
        elif isinstance(sole, str):
            sole_name = sole
            if sole_name in SOLE_GATE_EVENTS or sole_name in (
                "afterAgentResponse",
                "afterAgentThought",
                "stop",
            ):
                if not has_companion:
                    errors.append(
                        f"meta.sole_production_gate={sole_name!r} без companion "
                        "beforeShellExecution/subagentStart — sole conversation gate запрещён"
                    )
            # also fail if matrix marks sole_gate_forbidden and no companion
            row = matrix_by_name.get(sole_name)
            if row and row.get("sole_gate_forbidden") and not has_companion:
                if not any("sole_production_gate" in e for e in errors):
                    errors.append(
                        f"sole_gate_forbidden для {sole_name} без companion gate"
                    )

    # WARN: gate_candidate without observe sibling (soft)
    if has_gate_candidate and not has_observe:
        warnings.append(
            "есть gate_candidate без observe sibling "
            "(рекомендуется afterAgentResponse/afterFileEdit observe)"
        )

    ok = len(errors) == 0
    return {
        "ok": ok,
        "source": source,
        "errors": errors,
        "warnings": warnings,
        "events": present_events,
    }


def run_fixture_dir(
    fixture_dir: Path,
    matrix_by_name: dict[str, dict[str, Any]],
    *,
    require_cloud_safe: bool,
) -> dict[str, Any]:
    files = sorted(fixture_dir.glob("*.json"))
    results: list[dict[str, Any]] = []
    expectations_met = True

    if not files:
        return {
            "ok": False,
            "mode": "fixture-dir",
            "fixture_dir": str(fixture_dir),
            "errors": ["Нет *.json в fixture-dir"],
            "results": [],
        }

    for path in files:
        name = path.name
        try:
            data = load_json(path)
        except ValueError as exc:
            results.append(
                {
                    "file": name,
                    "ok": False,
                    "expected": "?",
                    "matched": False,
                    "errors": [str(exc)],
                    "warnings": [],
                }
            )
            expectations_met = False
            continue

        report = validate_hooks(
            data,
            matrix_by_name,
            require_cloud_safe=require_cloud_safe,
            source=name,
        )
        if name.startswith("ok-"):
            expected_ok = True
        elif name.startswith("bad-"):
            expected_ok = False
        else:
            # неизвестный префикс — требуем ok
            expected_ok = True
            report["warnings"] = list(report.get("warnings") or []) + [
                f"файл {name} без префикса ok-/bad-; ожидается PASS"
            ]

        matched = report["ok"] is expected_ok
        if not matched:
            expectations_met = False
        results.append(
            {
                "file": name,
                "ok": report["ok"],
                "expected_ok": expected_ok,
                "matched": matched,
                "errors": report.get("errors") or [],
                "warnings": report.get("warnings") or [],
            }
        )

    return {
        "ok": expectations_met,
        "mode": "fixture-dir",
        "fixture_dir": str(fixture_dir),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-800 cloud hooks smoke")
    parser.add_argument("--hooks", type=Path, help="Путь к hooks.json")
    parser.add_argument(
        "--matrix",
        type=Path,
        default=DEFAULT_MATRIX,
        help="Путь к cloud-hooks-matrix.json",
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        help="Каталог фикстур ok-*.json / bad-*.json",
    )
    parser.add_argument(
        "--require-cloud-safe",
        action="store_true",
        help="FAIL если есть local_only events",
    )
    args = parser.parse_args(argv)

    if not args.hooks and not args.fixture_dir:
        parser.error("Нужен --hooks PATH или --fixture-dir DIR")

    try:
        matrix = load_json(args.matrix)
        matrix_by_name = index_matrix(matrix)
    except ValueError as exc:
        summary = {"ok": False, "errors": [str(exc)]}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1

    if args.fixture_dir:
        summary = run_fixture_dir(
            args.fixture_dir,
            matrix_by_name,
            require_cloud_safe=args.require_cloud_safe,
        )
    else:
        try:
            data = load_json(args.hooks)
        except ValueError as exc:
            summary = {"ok": False, "source": str(args.hooks), "errors": [str(exc)]}
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 1
        report = validate_hooks(
            data,
            matrix_by_name,
            require_cloud_safe=args.require_cloud_safe,
            source=str(args.hooks),
        )
        summary = {
            "ok": report["ok"],
            "mode": "hooks",
            "matrix": str(args.matrix),
            **report,
            "policy": matrix.get("policy"),
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
