#!/usr/bin/env python3
"""Привязка t800_factory_bypass_gate.py к diff (C8): time-binding / files-coverage.

  python3 tests/test_bypass_gate_diff.py   # или pytest

Сценарии (temp plugin_root + memory, --files без git):
  1. stale-ts: factory completed с finished_at < mtime артефакта → exit 1
  2. time-binding: finished_at >= mtime → exit 0
  3. files-coverage: шаг без ts, но files[] покрывает артефакт → exit 0
  4. README (не артефакт) → exit 0
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "t800_factory_bypass_gate.py"


def _make_tree(base: Path, manifest: dict | None) -> tuple[Path, Path]:
    plugin = base / "plugin"
    mem = base / "memory"
    (plugin / "agents").mkdir(parents=True)
    mem.mkdir(parents=True)
    (plugin / "agents" / "x.md").write_text("# x\n", encoding="utf-8")
    (plugin / "README.md").write_text("r\n", encoding="utf-8")
    if manifest is not None:
        (mem / "run-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
    return plugin, mem


def _run_gate(plugin: Path, mem: Path, files: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--plugin-root",
            str(plugin),
            "--memory-path",
            str(mem),
            "--files",
            *files,
        ],
        capture_output=True,
        text=True,
    )


def _binding(proc: subprocess.CompletedProcess) -> str | None:
    # stdout = JSON summary + строка "PASS/FAIL: ..." — берём binding из JSON-блока
    match = re.search(r'"binding":\s*"(\w+)"', proc.stdout or "")
    return match.group(1) if match else None


def test_stale_ts_fails() -> None:
    with tempfile.TemporaryDirectory(prefix="t800-bypass-") as td:
        manifest = {
            "steps": [
                {
                    "agent": "t-800-factory",
                    "status": "completed",
                    "finished_at": "2020-01-01T00:00:00Z",
                }
            ]
        }
        plugin, mem = _make_tree(Path(td), manifest)
        now = time.time()
        import os

        os.utime(plugin / "agents" / "x.md", (now, now))
        proc = _run_gate(plugin, mem, ["agents/x.md"])
        assert proc.returncode == 1, f"stale-ts должен FAIL: {proc.stdout} {proc.stderr}"
        assert _binding(proc) == "none"


def test_time_binding_passes() -> None:
    with tempfile.TemporaryDirectory(prefix="t800-bypass-") as td:
        future = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600)
        )
        manifest = {
            "steps": [
                {"agent": "t-800-factory", "status": "ok", "finished_at": future}
            ]
        }
        plugin, mem = _make_tree(Path(td), manifest)
        past = time.time() - 3600
        import os

        os.utime(plugin / "agents" / "x.md", (past, past))
        proc = _run_gate(plugin, mem, ["agents/x.md"])
        assert proc.returncode == 0, f"time-binding должен PASS: {proc.stdout} {proc.stderr}"
        assert _binding(proc) == "time"


def test_files_coverage_passes() -> None:
    with tempfile.TemporaryDirectory(prefix="t800-bypass-") as td:
        manifest = {
            "steps": [
                {
                    "agent": "t-800-factory",
                    "status": "ok",
                    "files": ["agents/x.md"],
                }
            ]
        }
        plugin, mem = _make_tree(Path(td), manifest)
        proc = _run_gate(plugin, mem, ["agents/x.md"])
        assert proc.returncode == 0, f"coverage-only должен PASS: {proc.stdout} {proc.stderr}"
        assert _binding(proc) == "files"


def test_readme_non_artifact_passes() -> None:
    with tempfile.TemporaryDirectory(prefix="t800-bypass-") as td:
        plugin, mem = _make_tree(Path(td), None)
        proc = _run_gate(plugin, mem, ["README.md"])
        assert proc.returncode == 0, f"README должен PASS: {proc.stdout} {proc.stderr}"


def main() -> int:
    tests = [
        ("stale-ts → exit 1", test_stale_ts_fails),
        ("ts>=mtime → exit 0", test_time_binding_passes),
        ("coverage-only → exit 0", test_files_coverage_passes),
        ("README → exit 0", test_readme_non_artifact_passes),
    ]
    fails = 0
    for name, fn in tests:
        try:
            fn()
        except AssertionError as exc:
            print(f"FAIL {name}: {exc}", file=sys.stderr)
            fails += 1
        else:
            print(f"PASS {name}")
    if fails:
        print(f"FAIL: test_bypass_gate_diff ({fails} кейсов)", file=sys.stderr)
        return 1
    print("PASS: test_bypass_gate_diff")
    return 0


if __name__ == "__main__":
    sys.exit(main())
