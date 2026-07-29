#!/usr/bin/env python3
"""Тесты KPI telemetry schema 1.1: append → summarize → summary.json.

  python3 tests/test_telemetry_kpi.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TELEM = ROOT / "scripts" / "t800_telemetry.py"
FIXTURE = ROOT / "tests" / "fixtures" / "telemetry" / "sample-runs.jsonl"


def run_telem(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TELEM), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def main() -> int:
    if not TELEM.is_file():
        print("FAIL: нет scripts/t800_telemetry.py", file=sys.stderr)
        return 1
    if not FIXTURE.is_file():
        print("FAIL: нет tests/fixtures/telemetry/sample-runs.jsonl", file=sys.stderr)
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="t800-telem-kpi-"))
    try:
        # --- append 3 events ---
        for line in FIXTURE.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw:
                continue
            proc = run_telem(["--memory-path", str(tmp), "--event", raw])
            if proc.returncode != 0:
                print(proc.stdout)
                print(proc.stderr, file=sys.stderr)
                print("FAIL: append event", file=sys.stderr)
                return 1

        jsonl = tmp / "telemetry" / "runs.jsonl"
        if not jsonl.is_file():
            print("FAIL: runs.jsonl не создан", file=sys.stderr)
            return 1
        lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if len(lines) != 3:
            print(f"FAIL: ожидалось 3 строки JSONL, получено {len(lines)}", file=sys.stderr)
            return 1

        # --- summarize ---
        proc = run_telem(["--memory-path", str(tmp), "--summarize"])
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            print("FAIL: summarize exit != 0", file=sys.stderr)
            return 1

        try:
            summary = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print("FAIL: summarize не вернул JSON", file=sys.stderr)
            print(proc.stdout, file=sys.stderr)
            return 1

        if summary.get("count") != 3:
            print(f"FAIL: count={summary.get('count')}, ожидалось 3", file=sys.stderr)
            return 1
        if summary.get("count_missing_kpi") != 0:
            print(
                f"FAIL: count_missing_kpi={summary.get('count_missing_kpi')}, ожидалось 0",
                file=sys.stderr,
            )
            return 1

        dur = summary.get("duration_ms") or {}
        avg = dur.get("avg")
        if avg != 200.0:
            print(f"FAIL: duration_ms.avg={avg}, ожидалось 200.0", file=sys.stderr)
            return 1
        if dur.get("sum") != 600:
            print(f"FAIL: duration_ms.sum={dur.get('sum')}, ожидалось 600", file=sys.stderr)
            return 1
        if dur.get("p50") != 200.0:
            print(f"FAIL: duration_ms.p50={dur.get('p50')}, ожидалось 200.0", file=sys.stderr)
            return 1

        tokens = summary.get("tokens") or {}
        if tokens.get("in") != 90 or tokens.get("out") != 120:
            print(f"FAIL: tokens={tokens}, ожидалось in=90 out=120", file=sys.stderr)
            return 1

        retries = summary.get("retries") or {}
        if retries.get("sum") != 3:
            print(f"FAIL: retries.sum={retries.get('sum')}, ожидалось 3", file=sys.stderr)
            return 1

        summary_path = tmp / "telemetry" / "summary.json"
        if not summary_path.is_file():
            print("FAIL: summary.json не записан", file=sys.stderr)
            return 1
        on_disk = json.loads(summary_path.read_text(encoding="utf-8"))
        if on_disk.get("duration_ms", {}).get("avg") != 200.0:
            print("FAIL: summary.json avg != 200.0", file=sys.stderr)
            return 1

        # --- negative KPI → FAIL ---
        bad = run_telem(
            ["--memory-path", str(tmp), "--event", json.dumps({"duration_ms": -1})]
        )
        if bad.returncode == 0:
            print("FAIL: отрицательный duration_ms должен дать exit 1", file=sys.stderr)
            return 1

        # --- missing KPI still summarize exit 0 ---
        tmp2 = Path(tempfile.mkdtemp(prefix="t800-telem-miss-"))
        try:
            run_telem(
                [
                    "--memory-path",
                    str(tmp2),
                    "--event",
                    json.dumps({"event": "legacy", "status": "pass"}),
                ]
            )
            miss = run_telem(["--memory-path", str(tmp2), "--summarize"])
            if miss.returncode != 0:
                print("FAIL: summarize с missing KPI должен exit 0", file=sys.stderr)
                return 1
            miss_sum = json.loads(miss.stdout)
            if miss_sum.get("count_missing_kpi") != 1:
                print(
                    f"FAIL: count_missing_kpi={miss_sum.get('count_missing_kpi')}",
                    file=sys.stderr,
                )
                return 1
            strict = run_telem(
                ["--memory-path", str(tmp2), "--summarize", "--strict-kpi"]
            )
            if strict.returncode != 1:
                print("FAIL: --strict-kpi при 100% missing должен exit 1", file=sys.stderr)
                return 1
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

        print("PASS: test_telemetry_kpi")
        print(json.dumps({"ok": True, "avg": avg, "count": 3}, ensure_ascii=False))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
