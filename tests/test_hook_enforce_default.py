#!/usr/bin/env python3
"""Тесты before-artifact-edit.sh default enforce + opt-out warn.

  python3 tests/test_hook_enforce_default.py

Изоляция: копия hook в temp plugin_root без sibling t-800-memory
(иначе soft-bypass по factory completed в workspace memory).
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
HOOK_SRC = ROOT / "hooks" / "before-artifact-edit.sh"


def run_hook(
    hook_path: Path,
    cwd: Path,
    payload: dict,
    env_extra: dict[str, str] | None = None,
) -> dict:
    base = os.environ.copy()
    for k in (
        "T800_HOOK_MODE",
        "T800_TEYA_HOOK_MODE",
        "T800_FACTORY_RUN_ID",
        "T800_MEMORY_PATH",
    ):
        base.pop(k, None)
    if env_extra:
        base.update(env_extra)
    proc = subprocess.run(
        ["bash", str(hook_path)],
        input=json.dumps(payload),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=base,
    )
    raw = (proc.stdout or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "_parse_error": True,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }


def main() -> int:
    if not HOOK_SRC.is_file():
        print("FAIL: нет hooks/before-artifact-edit.sh", file=sys.stderr)
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="t800-hook-iso-"))
    try:
        hooks_dir = tmp / "hooks"
        hooks_dir.mkdir(parents=True)
        hook = hooks_dir / "before-artifact-edit.sh"
        shutil.copy(HOOK_SRC, hook)
        # isolated plugin_root: no ../t-800-memory with factory completed
        (tmp / "scripts").mkdir(exist_ok=True)

        artifact = {"filePath": "/tmp/proj/agents/x.md"}

        # default unset → deny
        out = run_hook(hook, tmp, artifact)
        if out.get("permission") != "deny":
            print(f"FAIL: default должен deny, got {out}", file=sys.stderr)
            return 1

        # warn opt-out → allow + userMessage
        out = run_hook(hook, tmp, artifact, {"T800_HOOK_MODE": "warn"})
        if out.get("permission") != "allow":
            print(f"FAIL: warn должен allow, got {out}", file=sys.stderr)
            return 1
        msg = out.get("userMessage") or ""
        if "WARN" not in msg:
            print(f"FAIL: warn без userMessage WARN: {out}", file=sys.stderr)
            return 1

        # observe → allow
        out = run_hook(hook, tmp, artifact, {"T800_HOOK_MODE": "observe"})
        if out.get("permission") != "allow":
            print(f"FAIL: observe должен allow, got {out}", file=sys.stderr)
            return 1

        # factory bypass
        out = run_hook(hook, tmp, artifact, {"T800_FACTORY_RUN_ID": "test-run"})
        if out.get("permission") != "allow":
            print(f"FAIL: factory bypass должен allow, got {out}", file=sys.stderr)
            return 1

        # non-artifact
        out = run_hook(hook, tmp, {"filePath": "/tmp/proj/src/app.py"})
        if out.get("permission") != "allow":
            print(f"FAIL: non-artifact должен allow, got {out}", file=sys.stderr)
            return 1

        # also invoke canonical path once (user contract): stdin agents path
        # with env cleaned — may allow if workspace memory has factory; assert JSON only
        base = os.environ.copy()
        for k in (
            "T800_HOOK_MODE",
            "T800_TEYA_HOOK_MODE",
            "T800_FACTORY_RUN_ID",
            "T800_MEMORY_PATH",
        ):
            base.pop(k, None)
        proc = subprocess.run(
            ["bash", str(HOOK_SRC)],
            input=json.dumps({"filePath": "/tmp/proj/agents/foo.md"}),
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=base,
        )
        try:
            json.loads((proc.stdout or "").strip())
        except json.JSONDecodeError:
            print("FAIL: canonical hook не вернул JSON", file=sys.stderr)
            print(proc.stdout, proc.stderr, file=sys.stderr)
            return 1

        print("PASS: test_hook_enforce_default")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
