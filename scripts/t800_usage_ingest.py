#!/usr/bin/env python3
"""t800_usage_ingest.py — bridge Cursor Usage UI / env → telemetry JSONL.

Merge priority (low → high): empty → --from-env → --from-file → CLI flags.
Writes event=usage_ingest, source=ui_or_env into {memory}/telemetry/runs.jsonl.

Usage:
  python3 scripts/t800_usage_ingest.py --memory-path PATH \\
    [--run-id ID] [--tokens-in N] [--tokens-out N] [--duration-ms N] \\
    [--from-env] [--from-file usage-draft.json]

Exit: 0 pass, 1 fail.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from t800_telemetry import append_event, normalize_kpi_fields  # noqa: E402

ENV_MAP = {
    "tokens_in": "T800_USAGE_TOKENS_IN",
    "tokens_out": "T800_USAGE_TOKENS_OUT",
    "duration_ms": "T800_USAGE_DURATION_MS",
    "run_id": "T800_USAGE_RUN_ID",
}
KPI_KEYS = ("tokens_in", "tokens_out", "duration_ms")


def parse_optional_int(raw: str | None, label: str) -> int | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        val = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} должен быть int >= 0, получено: {raw!r}") from exc
    if val < 0:
        raise ValueError(f"{label} должен быть int >= 0, получено: {val}")
    return val


def merge_layer(target: dict[str, Any], layer: dict[str, Any]) -> None:
    for key, val in layer.items():
        if val is None:
            continue
        if isinstance(val, str) and val.strip() == "":
            continue
        target[key] = val


def layer_from_env() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, env_name in ENV_MAP.items():
        raw = os.environ.get(env_name)
        if raw is None or str(raw).strip() == "":
            continue
        if key == "run_id":
            out[key] = str(raw).strip()
        else:
            out[key] = parse_optional_int(raw, env_name)
    return out


def layer_from_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"не удалось прочитать --from-file: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("--from-file должен быть JSON-объектом")
    out: dict[str, Any] = {}
    if "run_id" in data and data["run_id"] is not None:
        rid = data["run_id"]
        if str(rid).strip():
            out["run_id"] = str(rid).strip()
    for key in KPI_KEYS:
        if key not in data or data[key] is None:
            continue
        val = data[key]
        if isinstance(val, bool) or not isinstance(val, int):
            try:
                val = int(val)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{key} в файле должен быть int >= 0") from exc
        if val < 0:
            raise ValueError(f"{key} в файле должен быть int >= 0, получено: {val}")
        out[key] = val
    return out


def layer_from_cli(args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if args.run_id is not None and str(args.run_id).strip():
        out["run_id"] = str(args.run_id).strip()
    for key, attr in (
        ("tokens_in", "tokens_in"),
        ("tokens_out", "tokens_out"),
        ("duration_ms", "duration_ms"),
    ):
        val = getattr(args, attr, None)
        if val is not None:
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise ValueError(f"--{key.replace('_', '-')} должен быть int >= 0")
            out[key] = val
    return out


def build_event(merged: dict[str, Any]) -> dict[str, Any]:
    has_kpi = any(merged.get(k) is not None for k in KPI_KEYS)
    if not has_kpi:
        raise ValueError(
            "нужно хотя бы одно KPI-поле: tokens_in / tokens_out / duration_ms "
            "(CLI, --from-env или --from-file)"
        )
    event: dict[str, Any] = {
        "event": "usage_ingest",
        "source": "ui_or_env",
    }
    if merged.get("run_id"):
        event["run_id"] = merged["run_id"]
    for key in KPI_KEYS:
        if key in merged and merged[key] is not None:
            event[key] = merged[key]
    return normalize_kpi_fields(event)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T-800 usage ingest — UI/env/file → telemetry JSONL"
    )
    parser.add_argument("--memory-path", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--tokens-in", type=int, default=None)
    parser.add_argument("--tokens-out", type=int, default=None)
    parser.add_argument("--duration-ms", type=int, default=None)
    parser.add_argument("--from-env", action="store_true")
    parser.add_argument("--from-file", default=None, metavar="PATH")
    args = parser.parse_args()

    memory_path = Path(args.memory_path).expanduser().resolve()
    summary: dict[str, Any] = {
        "ok": True,
        "path": None,
        "event": None,
        "error": None,
    }

    try:
        merged: dict[str, Any] = {}
        if args.from_env:
            merge_layer(merged, layer_from_env())
        if args.from_file:
            file_path = Path(args.from_file).expanduser().resolve()
            if not file_path.is_file():
                raise ValueError(f"файл не найден: {file_path}")
            merge_layer(merged, layer_from_file(file_path))
        merge_layer(merged, layer_from_cli(args))

        event = build_event(merged)
        path = append_event(memory_path, event)
        summary["path"] = str(path)
        summary["event"] = event
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        summary["ok"] = False
        summary["error"] = str(exc)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
