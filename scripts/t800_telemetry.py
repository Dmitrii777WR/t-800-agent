#!/usr/bin/env python3
"""t800_telemetry.py — append-only JSONL telemetry (Loop Engineering v2, KPI 1.1).

Usage:
  python3 scripts/t800_telemetry.py --memory-path PATH --event JSON
  python3 scripts/t800_telemetry.py --memory-path PATH --event-file PATH
  echo '{...}' | python3 scripts/t800_telemetry.py --memory-path PATH --stdin
  python3 scripts/t800_telemetry.py --memory-path PATH --summarize [--strict-kpi]

Appends one JSON object per line to {memory}/telemetry/runs.jsonl.
--summarize: aggregates → {memory}/telemetry/summary.json + stdout JSON.
Exit: 0 pass, 1 fail. Fail-open callers may ignore exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.1"
DEFAULT_REL = "telemetry/runs.jsonl"
SUMMARY_REL = "telemetry/summary.json"
KPI_INT_FIELDS = ("duration_ms", "tokens_in", "tokens_out", "retries")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_event(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"невалидный JSON события: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("событие должно быть JSON-объектом")
    return data


def normalize_kpi_fields(event: dict[str, Any]) -> dict[str, Any]:
    """Если KPI-поле присутствует — оно должно быть int >= 0, иначе ValueError."""
    out = dict(event)
    for key in KPI_INT_FIELDS:
        if key not in out or out[key] is None:
            continue
        val = out[key]
        if isinstance(val, bool) or not isinstance(val, int):
            raise ValueError(f"{key} должен быть int >= 0, получено: {val!r}")
        if val < 0:
            raise ValueError(f"{key} должен быть int >= 0, получено: {val}")
    return out


def append_event(memory_path: Path, event: dict[str, Any], rel: str = DEFAULT_REL) -> Path:
    out = memory_path / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = normalize_kpi_fields(event)
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.setdefault("ts", utc_now())
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with open(out, "a", encoding="utf-8") as fh:
        try:
            if hasattr(os, "lockf"):
                os.lockf(fh.fileno(), os.F_LOCK, 0)
        except OSError:
            pass
        fh.write(line + "\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
        try:
            if hasattr(os, "lockf"):
                os.lockf(fh.fileno(), os.F_ULOCK, 0)
        except OSError:
            pass
    return out


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def read_jsonl_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"невалидный JSONL строка {lineno}: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"строка {lineno}: ожидался JSON-объект")
        events.append(obj)
    return events


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Агрегаты KPI. События без duration_ms валидны (append-only schema 1.0)."""
    durations: list[int] = []
    tokens_in = 0
    tokens_out = 0
    retries_vals: list[int] = []
    by_stage: dict[str, int] = {}
    missing_kpi = 0

    for ev in events:
        stage = ev.get("stage")
        if stage is not None and str(stage).strip():
            key = str(stage)
            by_stage[key] = by_stage.get(key, 0) + 1

        if "duration_ms" not in ev or ev.get("duration_ms") is None:
            missing_kpi += 1
        else:
            val = ev["duration_ms"]
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise ValueError(f"duration_ms должен быть int >= 0, получено: {val!r}")
            durations.append(val)

        for key, bucket in (("tokens_in", "in"), ("tokens_out", "out")):
            if key not in ev or ev.get(key) is None:
                continue
            val = ev[key]
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise ValueError(f"{key} должен быть int >= 0, получено: {val!r}")
            if bucket == "in":
                tokens_in += val
            else:
                tokens_out += val

        if "retries" in ev and ev.get("retries") is not None:
            val = ev["retries"]
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise ValueError(f"retries должен быть int >= 0, получено: {val!r}")
            retries_vals.append(val)

    count = len(events)
    dur_sum = sum(durations)
    dur_avg = (dur_sum / len(durations)) if durations else None
    retries_sum = sum(retries_vals)
    retries_avg = (retries_sum / len(retries_vals)) if retries_vals else None

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "count": count,
        "count_missing_kpi": missing_kpi,
        "duration_ms": {
            "sum": dur_sum,
            "avg": dur_avg,
            "p50": _median(durations),
            "n": len(durations),
        },
        "tokens": {"in": tokens_in, "out": tokens_out},
        "retries": {"sum": retries_sum, "avg": retries_avg, "n": len(retries_vals)},
        "by_stage": by_stage,
    }


def write_summary(memory_path: Path, summary: dict[str, Any]) -> Path:
    out = memory_path / SUMMARY_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def run_summarize(memory_path: Path, rel: str, strict_kpi: bool) -> tuple[dict[str, Any], int]:
    path = memory_path / rel
    events = read_jsonl_events(path)
    summary = summarize_events(events)
    summary["memory_path"] = str(memory_path)
    summary["source"] = str(path)
    summary_path = write_summary(memory_path, summary)
    summary["path"] = str(summary_path)
    summary["ok"] = True

    exit_code = 0
    if strict_kpi and events:
        missing_ratio = summary["count_missing_kpi"] / summary["count"]
        if missing_ratio > 0.5:
            summary["ok"] = False
            summary["strict_kpi"] = {
                "fail": True,
                "reason": "более 50% событий без duration_ms",
                "missing_ratio": missing_ratio,
            }
            exit_code = 1
        else:
            summary["strict_kpi"] = {"fail": False, "missing_ratio": missing_ratio}
    elif strict_kpi:
        summary["strict_kpi"] = {"fail": False, "missing_ratio": 0.0}

    return summary, exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="T-800 telemetry — append JSONL / summarize KPI")
    parser.add_argument("--memory-path", required=True)
    parser.add_argument("--event", default=None, help="JSON-строка события")
    parser.add_argument("--event-file", default=None, help="Путь к JSON-файлу события")
    parser.add_argument("--stdin", action="store_true", help="Читать JSON из stdin")
    parser.add_argument(
        "--rel",
        default=DEFAULT_REL,
        help=f"Относительный путь JSONL (default {DEFAULT_REL})",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Агрегировать JSONL → telemetry/summary.json + stdout",
    )
    parser.add_argument(
        "--strict-kpi",
        action="store_true",
        help="С --summarize: exit 1 если >50%% событий без duration_ms",
    )
    args = parser.parse_args()

    memory_path = Path(args.memory_path).expanduser().resolve()

    if args.summarize:
        try:
            summary, code = run_summarize(memory_path, args.rel, args.strict_kpi)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            if code != 0:
                print("FAIL: strict-kpi — слишком много событий без duration_ms", file=sys.stderr)
            return code
        except (OSError, ValueError) as exc:
            err = {"ok": False, "error": str(exc), "memory_path": str(memory_path)}
            print(json.dumps(err, ensure_ascii=False, indent=2))
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1

    summary: dict[str, Any] = {
        "ok": True,
        "memory_path": str(memory_path),
        "path": None,
        "error": None,
    }

    try:
        if args.event_file:
            raw = Path(args.event_file).expanduser().resolve().read_text(encoding="utf-8")
            event = load_event(raw)
        elif args.event:
            event = load_event(args.event)
        elif args.stdin or (not sys.stdin.isatty() and not args.event and not args.event_file):
            raw = sys.stdin.read()
            if not raw.strip():
                raise ValueError("пустой stdin / нет --event")
            event = load_event(raw)
        else:
            raise ValueError("нужен --event, --event-file, --stdin или --summarize")

        path = append_event(memory_path, event, rel=args.rel)
        summary["path"] = str(path)
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
