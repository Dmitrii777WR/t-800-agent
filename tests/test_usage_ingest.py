#!/usr/bin/env python3
"""Тесты usage ingest → telemetry JSONL.

  python3 tests/test_usage_ingest.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "scripts" / "t800_usage_ingest.py"


def run_ingest(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    base = os.environ.copy()
    # strip usage env to avoid bleed
    for k in (
        "T800_USAGE_TOKENS_IN",
        "T800_USAGE_TOKENS_OUT",
        "T800_USAGE_DURATION_MS",
        "T800_USAGE_RUN_ID",
    ):
        base.pop(k, None)
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(INGEST), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


def last_event(tmp: Path) -> dict:
    jsonl = tmp / "telemetry" / "runs.jsonl"
    lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return json.loads(lines[-1])


def main() -> int:
    if not INGEST.is_file():
        print("FAIL: нет scripts/t800_usage_ingest.py", file=sys.stderr)
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="t800-usage-ingest-"))
    try:
        # CLI only
        proc = run_ingest(
            [
                "--memory-path",
                str(tmp),
                "--tokens-in",
                "10",
                "--tokens-out",
                "20",
            ]
        )
        if proc.returncode != 0:
            print(proc.stdout, proc.stderr, file=sys.stderr)
            print("FAIL: CLI ingest", file=sys.stderr)
            return 1
        ev = last_event(tmp)
        if ev.get("event") != "usage_ingest" or ev.get("source") != "ui_or_env":
            print(f"FAIL: event shape {ev}", file=sys.stderr)
            return 1
        if ev.get("tokens_in") != 10 or ev.get("tokens_out") != 20:
            print(f"FAIL: tokens {ev}", file=sys.stderr)
            return 1

        # from-env
        tmp2 = Path(tempfile.mkdtemp(prefix="t800-usage-env-"))
        try:
            proc = run_ingest(
                ["--memory-path", str(tmp2), "--from-env"],
                env={
                    "T800_USAGE_TOKENS_IN": "5",
                    "T800_USAGE_TOKENS_OUT": "7",
                    "T800_USAGE_DURATION_MS": "100",
                    "T800_USAGE_RUN_ID": "env-run",
                },
            )
            if proc.returncode != 0:
                print(proc.stdout, proc.stderr, file=sys.stderr)
                print("FAIL: from-env", file=sys.stderr)
                return 1
            ev = last_event(tmp2)
            if ev.get("tokens_in") != 5 or ev.get("run_id") != "env-run":
                print(f"FAIL: from-env event {ev}", file=sys.stderr)
                return 1
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

        # from-file
        draft = tmp / "draft.json"
        draft.write_text(
            json.dumps(
                {"tokens_in": 1, "tokens_out": 2, "duration_ms": 30, "run_id": "file-run"}
            ),
            encoding="utf-8",
        )
        tmp3 = Path(tempfile.mkdtemp(prefix="t800-usage-file-"))
        try:
            proc = run_ingest(
                ["--memory-path", str(tmp3), "--from-file", str(draft)]
            )
            if proc.returncode != 0:
                print(proc.stdout, proc.stderr, file=sys.stderr)
                print("FAIL: from-file", file=sys.stderr)
                return 1
            ev = last_event(tmp3)
            if ev.get("tokens_out") != 2 or ev.get("run_id") != "file-run":
                print(f"FAIL: from-file event {ev}", file=sys.stderr)
                return 1
        finally:
            shutil.rmtree(tmp3, ignore_errors=True)

        # merge: env + file + CLI (CLI wins)
        tmp4 = Path(tempfile.mkdtemp(prefix="t800-usage-merge-"))
        try:
            draft2 = tmp4 / "d.json"
            draft2.write_text(
                json.dumps({"tokens_in": 100, "tokens_out": 200}),
                encoding="utf-8",
            )
            proc = run_ingest(
                [
                    "--memory-path",
                    str(tmp4),
                    "--from-env",
                    "--from-file",
                    str(draft2),
                    "--tokens-in",
                    "999",
                ],
                env={"T800_USAGE_TOKENS_IN": "11", "T800_USAGE_TOKENS_OUT": "22"},
            )
            if proc.returncode != 0:
                print(proc.stdout, proc.stderr, file=sys.stderr)
                print("FAIL: merge", file=sys.stderr)
                return 1
            ev = last_event(tmp4)
            if ev.get("tokens_in") != 999:
                print(f"FAIL: CLI should win tokens_in={ev.get('tokens_in')}", file=sys.stderr)
                return 1
            if ev.get("tokens_out") != 200:
                print(f"FAIL: file should win tokens_out={ev.get('tokens_out')}", file=sys.stderr)
                return 1
        finally:
            shutil.rmtree(tmp4, ignore_errors=True)

        # no KPI
        bad = run_ingest(["--memory-path", str(tmp), "--run-id", "x"])
        if bad.returncode == 0:
            print("FAIL: без KPI должен exit 1", file=sys.stderr)
            return 1

        # negative
        neg = run_ingest(
            ["--memory-path", str(tmp), "--tokens-in", "-1"]
        )
        if neg.returncode == 0:
            print("FAIL: отрицательный token должен exit 1", file=sys.stderr)
            return 1

        print("PASS: test_usage_ingest")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
