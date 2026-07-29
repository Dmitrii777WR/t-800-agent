#!/usr/bin/env python3
"""Тесты auto-LOW HITL gates + dry-run/apply.

  python3 tests/test_auto_low_hitl.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "scripts" / "t800_auto_low_batch.py"
APPROVE = ROOT / "scripts" / "t800_loop_hitl_approve.py"
FIXTURES = ROOT / "tests" / "fixtures" / "auto-low"


def run_py(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def setup_memory(tmp: Path, *, enabled: bool, hitl: bool, paused: bool = False) -> Path:
    policy_src = FIXTURES / (
        "policy.enabled.json" if enabled else "policy.disabled.json"
    )
    shutil.copy(policy_src, tmp / "loop-policy.json")
    lessons_dir = tmp / "runs" / "fixture-auto-low"
    lessons_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "lessons-sample.json", lessons_dir / "lessons.json")
    (tmp / "fix-packs").mkdir(parents=True, exist_ok=True)
    if hitl:
        (tmp / ".loop-auto-low-approved").write_text(
            json.dumps(
                {
                    "approved_at": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "by": "hitl",
                    "purpose": "auto_low",
                }
            )
            + "\n",
            encoding="utf-8",
        )
    if paused:
        (tmp / ".loop-paused").write_text("paused\n", encoding="utf-8")
    return lessons_dir / "lessons.json"


def pack_count(tmp: Path) -> int:
    d = tmp / "fix-packs"
    if not d.is_dir():
        return 0
    return len(list(d.glob("*.md")))


def main() -> int:
    if not BATCH.is_file() or not APPROVE.is_file():
        print("FAIL: нет auto_low / hitl scripts", file=sys.stderr)
        return 1
    if not (FIXTURES / "lessons-sample.json").is_file():
        print("FAIL: нет fixtures/auto-low", file=sys.stderr)
        return 1

    # no HITL
    tmp = Path(tempfile.mkdtemp(prefix="t800-al-nohitl-"))
    try:
        lessons = setup_memory(tmp, enabled=True, hitl=False)
        proc = run_py(
            BATCH,
            [
                "--memory-path",
                str(tmp),
                "--lessons",
                str(lessons),
                "--plugin-root",
                str(ROOT),
            ],
        )
        if proc.returncode == 0:
            print("FAIL: без HITL должен FAIL", file=sys.stderr)
            print(proc.stdout, file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # enabled=false
    tmp = Path(tempfile.mkdtemp(prefix="t800-al-off-"))
    try:
        lessons = setup_memory(tmp, enabled=False, hitl=True)
        proc = run_py(
            BATCH,
            [
                "--memory-path",
                str(tmp),
                "--lessons",
                str(lessons),
                "--plugin-root",
                str(ROOT),
            ],
        )
        if proc.returncode == 0:
            print("FAIL: enabled=false должен FAIL", file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # paused
    tmp = Path(tempfile.mkdtemp(prefix="t800-al-pause-"))
    try:
        lessons = setup_memory(tmp, enabled=True, hitl=True, paused=True)
        proc = run_py(
            BATCH,
            [
                "--memory-path",
                str(tmp),
                "--lessons",
                str(lessons),
                "--plugin-root",
                str(ROOT),
            ],
        )
        if proc.returncode == 0:
            print("FAIL: .loop-paused должен FAIL", file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # dry-run ok
    tmp = Path(tempfile.mkdtemp(prefix="t800-al-dry-"))
    try:
        lessons = setup_memory(tmp, enabled=True, hitl=True)
        before = pack_count(tmp)
        proc = run_py(
            BATCH,
            [
                "--memory-path",
                str(tmp),
                "--lessons",
                str(lessons),
                "--plugin-root",
                str(ROOT),
            ],
        )
        if proc.returncode != 0:
            print(proc.stdout, proc.stderr, file=sys.stderr)
            print("FAIL: dry-run с HITL+enabled", file=sys.stderr)
            return 1
        out = json.loads(proc.stdout)
        if out.get("mode") != "dry-run":
            print(f"FAIL: mode={out.get('mode')}", file=sys.stderr)
            return 1
        if pack_count(tmp) != before:
            print("FAIL: dry-run не должен писать packs", file=sys.stderr)
            return 1
        if "/t800-fix" not in (out.get("next") or []):
            print("FAIL: next должен содержать /t800-fix", file=sys.stderr)
            return 1
        blob = (proc.stdout + proc.stderr).lower()
        if "t-800-factory" in blob and "factory_invoked\": true" in blob.replace(" ", ""):
            print("FAIL: factory не должен вызываться", file=sys.stderr)
            return 1
        if out.get("factory_invoked") is True:
            print("FAIL: factory_invoked true", file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # apply
    tmp = Path(tempfile.mkdtemp(prefix="t800-al-apply-"))
    try:
        lessons = setup_memory(tmp, enabled=True, hitl=True)
        proc = run_py(
            BATCH,
            [
                "--memory-path",
                str(tmp),
                "--lessons",
                str(lessons),
                "--plugin-root",
                str(ROOT),
                "--apply",
            ],
        )
        if proc.returncode != 0:
            print(proc.stdout, proc.stderr, file=sys.stderr)
            print("FAIL: --apply", file=sys.stderr)
            return 1
        out = json.loads(proc.stdout)
        if pack_count(tmp) < 1:
            print("FAIL: --apply должен создать packs", file=sys.stderr)
            return 1
        log = tmp / "telemetry" / "auto-low-log.jsonl"
        if not log.is_file():
            print("FAIL: нет auto-low-log.jsonl", file=sys.stderr)
            return 1
        if "/t800-fix" not in (out.get("next") or []):
            print("FAIL: apply next=/t800-fix", file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # approve / revoke
    tmp = Path(tempfile.mkdtemp(prefix="t800-al-hitl-"))
    try:
        hitl = tmp / ".loop-auto-low-approved"
        ap = run_py(APPROVE, ["--memory-path", str(tmp), "--auto-low"])
        if ap.returncode != 0 or not hitl.is_file():
            print("FAIL: approve", file=sys.stderr)
            return 1
        rv = run_py(
            APPROVE, ["--memory-path", str(tmp), "--auto-low", "--revoke"]
        )
        if rv.returncode != 0 or hitl.is_file():
            print("FAIL: revoke", file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # daily budget exhausted
    tmp = Path(tempfile.mkdtemp(prefix="t800-al-budget-"))
    try:
        lessons = setup_memory(tmp, enabled=True, hitl=True)
        log_dir = tmp / "telemetry"
        log_dir.mkdir(parents=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines = []
        for i in range(3):
            lines.append(
                json.dumps(
                    {
                        "ts": f"{today}T0{i}:00:00Z",
                        "action": "batch_apply",
                        "count": 1,
                    }
                )
            )
        (log_dir / "auto-low-log.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        proc = run_py(
            BATCH,
            [
                "--memory-path",
                str(tmp),
                "--lessons",
                str(lessons),
                "--plugin-root",
                str(ROOT),
                "--apply",
            ],
        )
        if proc.returncode == 0:
            print("FAIL: budget exhausted должен FAIL", file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("PASS: test_auto_low_hitl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
