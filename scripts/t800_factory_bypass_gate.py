#!/usr/bin/env python3
"""t800_factory_bypass_gate.py — FAIL при правке Cursor-артефактов без factory.

Usage:
  python3 scripts/t800_factory_bypass_gate.py \\
      --plugin-root PATH --memory-path PATH \\
      [--files PATH ...] [--git-diff] [--base REF]

Exit 0 = нет обхода / нет артефактных изменений.
Exit 1 = найдены agents/skills/commands/rules без завершённого factory в manifest.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def fail(msg: str, summary: dict[str, Any], code: int = 1) -> int:
    summary["ok"] = False
    summary["error"] = msg
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"FAIL: {msg}", file=sys.stderr)
    return code


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _status_ok(value: Any) -> bool:
    return str(value or "").strip().lower() in {
        "ok",
        "done",
        "completed",
        "pass",
        "passed",
        "success",
    }


def factory_step_completed(manifest: dict[str, Any] | None) -> bool:
    if not manifest:
        return False
    for step in manifest.get("steps") or []:
        if not isinstance(step, dict):
            continue
        agent = str(step.get("agent") or step.get("name") or "").lower()
        if "factory" in agent and _status_ok(step.get("status")):
            return True
    factory = manifest.get("factory")
    if isinstance(factory, str) and _status_ok(factory):
        return True
    if isinstance(factory, dict) and _status_ok(factory.get("status")):
        return True
    return False


def _parse_ts(value: Any) -> float | None:
    """ISO 8601 → epoch. Суффикс 'Z' → +00:00; naive трактуется как local."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.astimezone().timestamp()
    return dt.timestamp()


def _norm_rel(path: str, plugin_root: Path) -> str:
    raw = path.replace("\\", "/")
    p = Path(raw)
    if p.is_absolute():
        try:
            raw = str(p.resolve().relative_to(plugin_root.resolve())).replace("\\", "/")
        except (ValueError, OSError):
            pass
    return raw.lstrip("./")


def _step_files(step: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for key in ("files", "artifacts", "changed_files", "paths"):
        val = step.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip():
                    out.add(item.replace("\\", "/").lstrip("./"))
    return out


def _completed_factory_steps(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for step in manifest.get("steps") or []:
        if not isinstance(step, dict):
            continue
        agent = str(step.get("agent") or step.get("name") or "").lower()
        if "factory" in agent and _status_ok(step.get("status")):
            steps.append(step)
    return steps


def factory_binding(
    manifest: dict[str, Any] | None,
    artifacts: list[str],
    plugin_root: Path,
) -> tuple[str, dict[str, Any] | None, float | None]:
    """Привязка factory-шага к изменённым артефактам.

    Возвращает (binding, matched_step, max_artifact_mtime):
      time  — finished_at||completed_at шага >= max(mtime артефактов)
      files — артефакты ⊆ files/artifacts/changed_files/paths шага
      none  — привязки нет → FAIL
    """
    max_mtime: float | None = None
    for rel in artifacts:
        p = Path(rel)
        if not p.is_absolute():
            p = plugin_root / rel
        try:
            mt = p.stat().st_mtime
        except OSError:
            continue
        max_mtime = mt if max_mtime is None else max(max_mtime, mt)
    if not manifest:
        return "none", None, max_mtime
    completed = _completed_factory_steps(manifest)
    if max_mtime is not None:
        for step in completed:
            ts = _parse_ts(step.get("finished_at")) or _parse_ts(
                step.get("completed_at")
            )
            if ts is not None and ts >= max_mtime:
                return "time", step, max_mtime
    norm = {_norm_rel(a, plugin_root) for a in artifacts}
    for step in completed:
        coverage = _step_files(step)
        if coverage and norm and norm <= coverage:
            return "files", step, max_mtime
    return "none", None, max_mtime


def is_cursor_artifact(rel_or_abs: str, plugin_root: Path) -> bool:
    """True for agents/*.md, skills/**/SKILL.md, commands/*.md, rules/*.mdc."""
    raw = rel_or_abs.replace("\\", "/")
    try:
        path = Path(raw)
        if path.is_absolute():
            try:
                rel = path.resolve().relative_to(plugin_root.resolve())
                raw = str(rel).replace("\\", "/")
            except ValueError:
                # outside plugin_root — still match by path segments
                pass
    except OSError:
        pass

    lower = raw.lstrip("./")
    name = Path(lower).name

    if "/agents/" in f"/{lower}" or lower.startswith("agents/"):
        return name.endswith(".md")
    if "/commands/" in f"/{lower}" or lower.startswith("commands/"):
        return name.endswith(".md")
    if lower.endswith("/SKILL.md") or name == "SKILL.md":
        if "/skills/" in f"/{lower}" or lower.startswith("skills/"):
            return True
        if "/.cursor/skills/" in f"/{lower}":
            return True
    if name.endswith(".mdc"):
        if (
            "/rules/" in f"/{lower}"
            or lower.startswith("rules/")
            or "/.cursor/rules/" in f"/{lower}"
        ):
            return True
    # hooks.json / hooks/*.sh — optional enforcement surface from pack
    if lower in ("hooks.json",) or lower.startswith("hooks/"):
        if name.endswith((".sh", ".json", ".ps1")) or name == "hooks.json":
            return True
    return False


def collect_git_changed(plugin_root: Path, base: str | None) -> list[str]:
    files: list[str] = []
    cmds: list[list[str]] = [
        ["git", "-C", str(plugin_root), "diff", "--name-only", "--diff-filter=ACMR"],
        [
            "git",
            "-C",
            str(plugin_root),
            "diff",
            "--name-only",
            "--cached",
            "--diff-filter=ACMR",
        ],
        [
            "git",
            "-C",
            str(plugin_root),
            "ls-files",
            "--others",
            "--exclude-standard",
        ],
    ]
    if base:
        cmds.insert(
            0,
            [
                "git",
                "-C",
                str(plugin_root),
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                f"{base}...HEAD",
            ],
        )
    seen: set[str] = set()
    for cmd in cmds:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            continue
        if proc.returncode != 0:
            continue
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                files.append(line)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate: Cursor-артефакты без factory step в run-manifest → FAIL."
    )
    parser.add_argument("--plugin-root", required=True, help="Корень плагина")
    parser.add_argument("--memory-path", required=True, help="Memory прогона")
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Явный список путей (относительных к plugin-root или абсолютных)",
    )
    parser.add_argument(
        "--git-diff",
        action="store_true",
        help="Собрать изменённые файлы через git (working tree + untracked)",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Git base ref для diff base...HEAD (с --git-diff)",
    )
    args = parser.parse_args()

    plugin_root = Path(args.plugin_root).expanduser().resolve()
    memory_path = Path(args.memory_path).expanduser().resolve()
    summary: dict[str, Any] = {
        "ok": True,
        "plugin_root": str(plugin_root),
        "memory_path": str(memory_path),
        "artifact_changes": [],
        "factory_completed": False,
        "checks": {},
        "error": None,
    }

    if not plugin_root.is_dir():
        return fail(f"plugin-root не найден: {plugin_root}", summary)

    candidates: list[str] = []
    if args.files:
        candidates.extend(args.files)
    # Без --files: сканируем git. С --files: git только если явно --git-diff.
    if args.git_diff or not args.files:
        candidates.extend(collect_git_changed(plugin_root, args.base))

    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for item in candidates:
        key = item.replace("\\", "/")
        if key not in seen:
            seen.add(key)
            uniq.append(item)

    artifacts = [p for p in uniq if is_cursor_artifact(p, plugin_root)]
    summary["artifact_changes"] = artifacts
    summary["checks"]["artifact_scan"] = f"count={len(artifacts)}"

    if not artifacts:
        summary["checks"]["bypass"] = "none"
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("PASS: t800_factory_bypass_gate (нет артефактных изменений)")
        return 0

    manifest_path = memory_path / "run-manifest.json"
    manifest = _load_json(manifest_path) if manifest_path.is_file() else None
    completed = factory_step_completed(manifest)
    binding, matched_step, max_mtime = factory_binding(manifest, artifacts, plugin_root)
    summary["factory_completed"] = completed
    summary["checks"]["manifest"] = (
        "ok" if completed else ("missing" if manifest is None else "factory_incomplete")
    )
    summary["checks"]["binding"] = binding
    summary["max_artifact_mtime"] = max_mtime
    summary["matched_step"] = (
        {
            "agent": matched_step.get("agent") or matched_step.get("name"),
            "finished_at": matched_step.get("finished_at")
            or matched_step.get("completed_at"),
        }
        if matched_step is not None
        else None
    )

    if binding != "none":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"PASS: t800_factory_bypass_gate (binding={binding})")
        return 0

    listed = ", ".join(artifacts[:12])
    more = "" if len(artifacts) <= 12 else f" (+{len(artifacts) - 12})"
    return fail(
        "Обход factory: изменены Cursor-артефакты без завершённого шага "
        "t-800-factory, привязанного к этим правкам (time-binding: finished_at/"
        "completed_at >= mtime артефактов; или files-coverage шага). "
        f"Файлы: {listed}{more}. "
        "Запустите /t800-start или /t800-fix → Task(t-800-factory). "
        "Не пишите agents/skills/commands/rules/hooks из main chat.",
        summary,
    )


if __name__ == "__main__":
    sys.exit(main())
