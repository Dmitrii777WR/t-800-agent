#!/usr/bin/env python3
"""t800_auto_low_batch.py — generate LOW fix-packs after HITL (never factory).

Gates: not paused, auto_low.enabled=true, HITL file present, daily_budget.
Default: --dry-run. --apply writes fix-packs only via lessons_to_fixpack.

Usage:
  python3 scripts/t800_auto_low_batch.py --memory-path PATH \\
    [--lessons PATH|run_id] [--plugin-root PATH] [--dry-run] [--apply]

Exit: 0 pass, 1 fail.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT_DEFAULT = SCRIPT_DIR.parent
LESSONS_TO_FIXPACK = SCRIPT_DIR / "t800_lessons_to_fixpack.py"
AUTO_LOW_LOG = Path("telemetry") / "auto-low-log.jsonl"
DEFAULT_HITL = ".loop-auto-low-approved"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fail(summary: dict[str, Any], msg: str) -> int:
    summary["ok"] = False
    summary["error"] = msg
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def load_policy(memory_path: Path) -> dict[str, Any]:
    path = memory_path / "loop-policy.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"нет loop-policy.json в памяти: {path} "
            "(скопируйте из templates/loop-policy.json.template)"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("loop-policy.json должен быть JSON-объектом")
    return data


def count_today_budget(log_path: Path) -> int:
    if not log_path.is_file():
        return 0
    today = utc_today()
    count = 0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        ts = str(obj.get("ts") or "")
        if not ts.startswith(today):
            continue
        action = str(obj.get("action") or "")
        if action in ("apply", "batch_apply"):
            count += 1
    return count


def resolve_lessons(memory_path: Path, arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser()
        if p.is_file():
            return p.resolve()
        candidate = memory_path / "runs" / arg / "lessons.json"
        if candidate.is_file():
            return candidate.resolve()
        raise FileNotFoundError(f"нет lessons.json: {arg}")

    runs = memory_path / "runs"
    if not runs.is_dir():
        raise FileNotFoundError("нет --lessons и нет {memory}/runs/")
    candidates: list[Path] = []
    for child in runs.iterdir():
        lesson = child / "lessons.json"
        if lesson.is_file():
            candidates.append(lesson)
    if not candidates:
        raise FileNotFoundError("нет lessons.json под {memory}/runs/")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def append_log(log_path: Path, entry: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="T-800 auto-LOW batch — fix-packs only after HITL"
    )
    parser.add_argument("--memory-path", required=True)
    parser.add_argument("--lessons", default=None)
    parser.add_argument("--plugin-root", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview (default если нет --apply)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Записать fix-packs (не вызывает factory)",
    )
    args = parser.parse_args()

    if args.apply and args.dry_run:
        print("FAIL: нельзя одновременно --apply и --dry-run", file=sys.stderr)
        return 1

    mode = "apply" if args.apply else "dry-run"
    memory_path = Path(args.memory_path).expanduser().resolve()
    plugin_root = (
        Path(args.plugin_root).expanduser().resolve()
        if args.plugin_root
        else PLUGIN_ROOT_DEFAULT
    )

    summary: dict[str, Any] = {
        "ok": True,
        "mode": mode,
        "created": [],
        "next": ["/t800-fix"],
        "packs": [],
        "budget_remaining": None,
        "error": None,
        "factory_invoked": False,
    }

    try:
        # Gate 1: paused
        if (memory_path / ".loop-paused").exists():
            return fail(summary, "loop на паузе (.loop-paused) — auto-LOW запрещён")

        policy = load_policy(memory_path)
        auto_low = policy.get("auto_low") or {}
        if not isinstance(auto_low, dict):
            return fail(summary, "loop-policy.auto_low должен быть объектом")

        # Gate 3: enabled
        if auto_low.get("enabled") is not True:
            return fail(
                summary,
                "auto_low.enabled != true — включите в loop-policy.json после HITL",
            )

        hitl_name = str(auto_low.get("require_hitl_file") or DEFAULT_HITL)
        hitl_path = memory_path / hitl_name
        # Gate 4: HITL
        if not hitl_path.is_file():
            return fail(
                summary,
                f"нет HITL-файла {hitl_name} — "
                "python3 scripts/t800_loop_hitl_approve.py --memory-path … --auto-low",
            )

        daily_budget = int(auto_low.get("daily_budget") or 3)
        max_per_batch = int(auto_low.get("max_per_batch") or 3)
        log_path = memory_path / AUTO_LOW_LOG
        used = count_today_budget(log_path)
        remaining = max(0, daily_budget - used)
        summary["budget_remaining"] = remaining

        # Gate 5: budget
        if remaining <= 0:
            return fail(
                summary,
                f"daily_budget исчерпан ({used}/{daily_budget} за сегодня UTC)",
            )

        effective_max = min(max_per_batch, remaining)
        lessons_path = resolve_lessons(memory_path, args.lessons)
        summary["lessons"] = str(lessons_path)

        if not LESSONS_TO_FIXPACK.is_file():
            return fail(summary, f"нет скрипта {LESSONS_TO_FIXPACK}")

        cmd = [
            sys.executable,
            str(LESSONS_TO_FIXPACK),
            "--memory-path",
            str(memory_path),
            "--lessons",
            str(lessons_path),
            "--plugin-root",
            str(plugin_root),
        ]
        if mode == "dry-run":
            cmd.append("--dry-run")

        proc = subprocess.run(
            cmd,
            cwd=str(plugin_root),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            summary["subprocess_stderr"] = (proc.stderr or "")[:500]
            return fail(
                summary,
                f"t800_lessons_to_fixpack.py exit {proc.returncode}",
            )

        try:
            child = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return fail(summary, "t800_lessons_to_fixpack.py вернул не-JSON")

        created = list(child.get("created") or [])
        if len(created) > effective_max:
            surplus = created[effective_max:]
            created = created[:effective_max]
            if mode == "apply":
                for item in surplus:
                    p = Path(str(item.get("path") or ""))
                    if p.is_file():
                        try:
                            p.unlink()
                        except OSError:
                            pass
            summary["truncated_to_max_per_batch"] = effective_max

        summary["created"] = created
        summary["packs"] = [str(c.get("slug") or "") for c in created if c.get("slug")]
        summary["next"] = ["/t800-fix"]
        summary["budget_remaining"] = remaining - (len(created) if mode == "apply" else 0)

        if mode == "apply" and created:
            append_log(
                log_path,
                {
                    "ts": utc_now(),
                    "action": "batch_apply",
                    "count": len(created),
                    "slugs": summary["packs"],
                    "run_id": None,
                },
            )

        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, FileNotFoundError, TypeError) as exc:
        return fail(summary, str(exc))


if __name__ == "__main__":
    sys.exit(main())
