#!/usr/bin/env python3
"""Тесты before-artifact-edit.sh (preToolUse) default enforce + opt-out warn.

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

        artifact = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/proj/agents/x.md"},
            "cwd": "/tmp/proj",
        }

        # default unset → deny (preToolUse schema: user_message + agent_message)
        out = run_hook(hook, tmp, artifact)
        if out.get("permission") != "deny":
            print(f"FAIL: default должен deny, got {out}", file=sys.stderr)
            return 1
        if not out.get("user_message") or not out.get("agent_message"):
            print(f"FAIL: deny без user_message/agent_message: {out}", file=sys.stderr)
            return 1
        if "userMessage" in out or "continue" in out:
            print(f"FAIL: legacy поля в deny payload: {out}", file=sys.stderr)
            return 1

        # warn opt-out → allow + user_message WARN
        out = run_hook(hook, tmp, artifact, {"T800_HOOK_MODE": "warn"})
        if out.get("permission") != "allow":
            print(f"FAIL: warn должен allow, got {out}", file=sys.stderr)
            return 1
        msg = out.get("user_message") or ""
        if "WARN" not in msg:
            print(f"FAIL: warn без user_message WARN: {out}", file=sys.stderr)
            return 1
        if "WARN" not in (out.get("agent_message") or ""):
            print(f"FAIL: warn без agent_message WARN: {out}", file=sys.stderr)
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
        out = run_hook(
            hook,
            tmp,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/tmp/proj/src/app.py"},
                "cwd": "/tmp/proj",
            },
        )
        if out.get("permission") != "allow":
            print(f"FAIL: non-artifact должен allow, got {out}", file=sys.stderr)
            return 1

        # preToolUse payload smoke: 5 вариантов пути → deny; пусто → allow (fail-open)
        variants = [
            {"tool_name": "Write", "tool_input": {"file_path": "/tmp/proj/agents/v1.md"}},
            {"tool_name": "StrReplace", "tool_input": {"path": "/tmp/proj/agents/v2.md"}},
            {
                "tool_name": "EditNotebook",
                "tool_input": {"target_notebook": "/tmp/proj/agents/v3.md"},
            },
            {"filePath": "/tmp/proj/agents/v4.md"},  # legacy top-level
            {"path": "/tmp/proj/agents/v5.md"},  # legacy top-level
        ]
        for idx, payload in enumerate(variants, 1):
            out = run_hook(hook, tmp, payload)
            if out.get("permission") != "deny":
                print(f"FAIL: вариант {idx} должен deny, got {out}", file=sys.stderr)
                return 1
        out = run_hook(hook, tmp, {})
        if out.get("permission") != "allow":
            print(f"FAIL: пустой payload должен allow (fail-open), got {out}", file=sys.stderr)
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
            input=json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": "/tmp/proj/agents/foo.md"},
                    "cwd": str(ROOT),
                }
            ),
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
