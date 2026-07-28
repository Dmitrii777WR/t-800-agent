#!/usr/bin/env python3
"""CONTENT_DRIFT sync: workspace plugin_root ↔ live plugins/local/t-800-agent.

--check:
  sha256 по дереву (НЕ mtime). Exclude: .git, __pycache__, *.pyc, .DS_Store,
  t-800-memory, *.egg-info.

default / --apply:
  subprocess bash scripts/install-plugin.sh (MIR только ~/.cursor/plugins/local).
  BAN: этот скрипт НЕ пишет в ~/.cursor/{agents,skills,rules,commands}.
  После apply — всегда напоминание Reload Window.

stdout JSON: {ok, drift:[], applied, reload_required, error?}
exit 0/1

CLI: --plugin-root PATH [--check | --apply] [--live PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

EXCLUDE_DIR_NAMES = {".git", "__pycache__", "t-800-memory"}
EXCLUDE_FILE_NAMES = {".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc", ".egg-info"}

BAN_USER_HOME_MIRRORS = ("agents", "skills", "rules", "commands")

RELOAD_REMINDER = (
    "⚠ Перезапустите Cursor: Command Palette → Developer: Reload Window"
)


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _should_skip(rel: Path) -> bool:
    parts = rel.parts
    for p in parts:
        if p in EXCLUDE_DIR_NAMES:
            return True
        if p.endswith(".egg-info"):
            return True
    name = rel.name
    if name in EXCLUDE_FILE_NAMES:
        return True
    if any(name.endswith(suf) for suf in EXCLUDE_SUFFIXES):
        return True
    return False


def _walk_hashes(root: Path) -> dict[str, str]:
    """relative posix path → sha256. CONTENT only (не mtime)."""
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs in-place
        dirnames[:] = [
            d
            for d in dirnames
            if d not in EXCLUDE_DIR_NAMES and not d.endswith(".egg-info")
        ]
        base = Path(dirpath)
        for fn in filenames:
            full = base / fn
            try:
                rel = full.relative_to(root)
            except ValueError:
                continue
            if _should_skip(rel):
                continue
            if not full.is_file() or full.is_symlink():
                # follow regular files only; skip broken/odd
                if not full.is_file():
                    continue
            try:
                out[rel.as_posix()] = _sha256_file(full)
            except OSError:
                continue
    return out


def _content_drift(src: Path, live: Path) -> list[dict[str, str]]:
    src_map = _walk_hashes(src)
    live_map = _walk_hashes(live)
    drift: list[dict[str, str]] = []
    all_keys = sorted(set(src_map) | set(live_map))
    for key in all_keys:
        s = src_map.get(key)
        l = live_map.get(key)
        if s is None:
            drift.append({"path": key, "kind": "live_only"})
        elif l is None:
            drift.append({"path": key, "kind": "workspace_only"})
        elif s != l:
            drift.append({"path": key, "kind": "hash_mismatch"})
    return drift


def _assert_no_ban_writes(plugin_root: Path) -> None:
    """Defence: sync must never target user-home artifact mirrors."""
    # Documented BAN — install-plugin MIR dest is plugins/local only.
    # We refuse if someone points --live at ~/.cursor/agents etc.
    home_cursor = Path.home() / ".cursor"
    for name in BAN_USER_HOME_MIRRORS:
        banned = (home_cursor / name).resolve()
        # no-op check placeholder; real guard is on --live below
        _ = banned


def _apply_install(plugin_root: Path) -> tuple[bool, str | None]:
    sh = plugin_root / "scripts" / "install-plugin.sh"
    if not sh.is_file():
        return False, f"нет {sh}"
    try:
        proc = subprocess.run(
            ["bash", str(sh)],
            cwd=str(plugin_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, f"не удалось запустить install-plugin.sh: {exc}"
    if proc.stdout:
        sys.stderr.write(proc.stdout)
        if not proc.stdout.endswith("\n"):
            sys.stderr.write("\n")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        if not proc.stderr.endswith("\n"):
            sys.stderr.write("\n")
    if proc.returncode != 0:
        return False, f"install-plugin.sh exit {proc.returncode}"
    return True, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plugin-root", type=Path, default=Path("."))
    ap.add_argument(
        "--live",
        type=Path,
        default=None,
        help="Путь live-плагина (default: ~/.cursor/plugins/local/t-800-agent)",
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Только CONTENT_DRIFT (sha256), без apply",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Применить install-plugin.sh (default если нет --check)",
    )
    args = ap.parse_args()

    plugin_root = args.plugin_root.expanduser().resolve()
    live = (
        args.live.expanduser().resolve()
        if args.live
        else (Path.home() / ".cursor" / "plugins" / "local" / "t-800-agent").resolve()
    )

    # BAN: --live не должен указывать на user-home mirrors
    home_cursor = (Path.home() / ".cursor").resolve()
    for name in BAN_USER_HOME_MIRRORS:
        banned = (home_cursor / name).resolve()
        try:
            live.relative_to(banned)
            err = (
                f"BAN: --live не может быть ~/.cursor/{name} "
                f"(только plugins/local MIR)"
            )
            _eprint(f"❌ PLUGIN SYNC FAIL — {err}")
            print(
                json.dumps(
                    {
                        "ok": False,
                        "drift": [],
                        "applied": False,
                        "reload_required": False,
                        "error": err,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        except ValueError:
            pass

    _assert_no_ban_writes(plugin_root)

    do_check_only = args.check
    do_apply = args.apply or not args.check  # default = apply

    if not plugin_root.is_dir():
        err = f"plugin_root не каталог: {plugin_root}"
        _eprint(f"❌ PLUGIN SYNC FAIL — {err}")
        print(
            json.dumps(
                {
                    "ok": False,
                    "drift": [],
                    "applied": False,
                    "reload_required": False,
                    "error": err,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    drift = _content_drift(plugin_root, live)

    if do_check_only:
        ok = len(drift) == 0
        if ok:
            _eprint(
                f"✅ PLUGIN SYNC CHECK PASS — CONTENT_DRIFT=0 "
                f"(workspace ↔ {live})"
            )
        else:
            _eprint(
                f"❌ PLUGIN SYNC CHECK FAIL — CONTENT_DRIFT={len(drift)} "
                f"(sha256, не mtime)"
            )
            for item in drift[:20]:
                _eprint(f"  • {item['kind']}: {item['path']}")
            if len(drift) > 20:
                _eprint(f"  … и ещё {len(drift) - 20}")
        print(
            json.dumps(
                {
                    "ok": ok,
                    "drift": drift,
                    "applied": False,
                    "reload_required": False,
                    "error": None if ok else f"CONTENT_DRIFT={len(drift)}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if ok else 1

    # apply path
    assert do_apply
    ok_install, err = _apply_install(plugin_root)
    _eprint(RELOAD_REMINDER)
    if not ok_install:
        _eprint(f"❌ PLUGIN SYNC APPLY FAIL — {err}")
        print(
            json.dumps(
                {
                    "ok": False,
                    "drift": drift,
                    "applied": False,
                    "reload_required": True,
                    "error": err,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    # re-check after apply
    post_drift = _content_drift(plugin_root, live)
    ok = len(post_drift) == 0
    if ok:
        _eprint("✅ PLUGIN SYNC APPLY PASS — live обновлён, Reload Window обязателен")
    else:
        _eprint(
            f"⚠ PLUGIN SYNC APPLY: install ок, но residual drift={len(post_drift)}"
        )
    print(
        json.dumps(
            {
                "ok": ok,
                "drift": post_drift,
                "applied": True,
                "reload_required": True,
                "error": None if ok else f"residual CONTENT_DRIFT={len(post_drift)}",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
