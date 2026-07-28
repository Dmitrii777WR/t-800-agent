#!/usr/bin/env python3
"""Gate: shared/command-chains.json ↔ commands/*.md ↔ registry agent ids.

Orphans FAIL:
  1) commands/*.md stem без ключа в commands{}
  2) ключ chains без commands/<stem>.md
  3) agent refs в chains ∉ registry ids (если registry есть)

--warn-soft: agent в registry ни разу не referenced в chains → WARN на stderr, exit 0
  (не FAIL P0).

Stdout: JSON {ok, checks, orphans, error?}
Stderr: RU-сообщения
Exit: 0 PASS / 1 FAIL

CLI: --plugin-root PATH [--warn-soft]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

AGENT_ID_RE = re.compile(r"^[a-z][a-z0-9_-]+$")
TASK_RE = re.compile(r"Task\(\s*([a-z][a-z0-9_-]+)\s*\)")

AGENT_LIST_KEYS = {
    "agents",
    "primary_agents",
    "optional_agents",
    "required_agents",
    "chain",
}


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _normalize_stem(key: str) -> str:
    s = key.strip()
    if s.startswith("/"):
        s = s[1:]
    return s


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_agent_refs(obj: Any, into: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "lead" and isinstance(v, str) and AGENT_ID_RE.match(v):
                into.add(v)
            if k in AGENT_LIST_KEYS and isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and AGENT_ID_RE.match(item):
                        into.add(item)
                    elif isinstance(item, dict):
                        aid = item.get("id") or item.get("agent") or item.get("name")
                        if isinstance(aid, str) and AGENT_ID_RE.match(aid):
                            into.add(aid)
            _collect_agent_refs(v, into)
    elif isinstance(obj, list):
        for item in obj:
            _collect_agent_refs(item, into)
    elif isinstance(obj, str):
        for m in TASK_RE.finditer(obj):
            into.add(m.group(1))


def _registry_ids(plugin_root: Path) -> set[str] | None:
    candidates = [
        plugin_root / "registry" / "agents-registry.json",
        plugin_root / "agents-registry.json",
    ]
    for cand in candidates:
        if not cand.is_file():
            continue
        try:
            data = _load_json(cand)
        except (OSError, json.JSONDecodeError) as exc:
            _eprint(f"⚠ registry не читается ({cand.name}): {exc}")
            return set()
        ids: set[str] = set()
        if isinstance(data, dict):
            agents = data.get("agents", [])
            if isinstance(agents, list):
                for item in agents:
                    if isinstance(item, dict):
                        aid = item.get("id")
                        if isinstance(aid, str):
                            ids.add(aid)
        return ids
    return None


def _command_stems_on_disk(commands_dir: Path) -> set[str]:
    if not commands_dir.is_dir():
        return set()
    return {p.stem for p in commands_dir.glob("*.md") if p.is_file()}


def run_gate(plugin_root: Path, warn_soft: bool) -> dict[str, Any]:
    chains_path = plugin_root / "shared" / "command-chains.json"
    commands_dir = plugin_root / "commands"
    checks: dict[str, Any] = {
        "chains_path": "shared/command-chains.json",
        "chains_present": False,
        "commands_on_disk": 0,
        "chain_keys": 0,
        "registry_present": False,
        "agent_refs": 0,
    }
    orphans: dict[str, list[str]] = {
        "cmd_without_chain": [],
        "chain_without_cmd": [],
        "agent_not_in_registry": [],
        "soft_unreferenced_registry": [],
    }

    if not chains_path.is_file():
        err = f"нет файла {chains_path.relative_to(plugin_root)}"
        _eprint(f"❌ COMMAND CHAINS GATE FAIL — {err}")
        return {
            "ok": False,
            "checks": checks,
            "orphans": orphans,
            "error": err,
        }

    checks["chains_present"] = True
    try:
        data = _load_json(chains_path)
    except json.JSONDecodeError as exc:
        err = f"JSON parse FAIL: {exc}"
        _eprint(f"❌ COMMAND CHAINS GATE FAIL — {err}")
        return {
            "ok": False,
            "checks": checks,
            "orphans": orphans,
            "error": err,
        }
    except OSError as exc:
        err = f"не удалось прочитать command-chains.json: {exc}"
        _eprint(f"❌ COMMAND CHAINS GATE FAIL — {err}")
        return {
            "ok": False,
            "checks": checks,
            "orphans": orphans,
            "error": err,
        }

    if not isinstance(data, dict):
        err = "command-chains.json: корень не object"
        _eprint(f"❌ COMMAND CHAINS GATE FAIL — {err}")
        return {
            "ok": False,
            "checks": checks,
            "orphans": orphans,
            "error": err,
        }

    cmds_obj = data.get("commands", {})
    if not isinstance(cmds_obj, dict):
        err = "command-chains.json: commands не object"
        _eprint(f"❌ COMMAND CHAINS GATE FAIL — {err}")
        return {
            "ok": False,
            "checks": checks,
            "orphans": orphans,
            "error": err,
        }

    chain_stems = {_normalize_stem(k) for k in cmds_obj.keys()}
    disk_stems = _command_stems_on_disk(commands_dir)
    checks["commands_on_disk"] = len(disk_stems)
    checks["chain_keys"] = len(chain_stems)

    orphans["cmd_without_chain"] = sorted(disk_stems - chain_stems)
    orphans["chain_without_cmd"] = sorted(chain_stems - disk_stems)

    agent_refs: set[str] = set()
    _collect_agent_refs(cmds_obj, agent_refs)
    checks["agent_refs"] = len(agent_refs)

    registry_ids = _registry_ids(plugin_root)
    if registry_ids is not None:
        checks["registry_present"] = True
        orphans["agent_not_in_registry"] = sorted(
            r for r in agent_refs if r not in registry_ids and r != "main-agent"
        )
        soft = sorted(
            rid
            for rid in registry_ids
            if rid not in agent_refs and rid != "main-agent"
        )
        orphans["soft_unreferenced_registry"] = soft
        if warn_soft and soft:
            _eprint(
                f"⚠ soft: {len(soft)} agent(s) в registry не referenced в chains "
                f"(первые: {', '.join(soft[:5])}{'…' if len(soft) > 5 else ''})"
            )

    hard_fail = (
        orphans["cmd_without_chain"]
        or orphans["chain_without_cmd"]
        or orphans["agent_not_in_registry"]
    )
    if hard_fail:
        _eprint("❌ COMMAND CHAINS GATE FAIL — orphans")
        if orphans["cmd_without_chain"]:
            _eprint(
                f"  • commands без ключа в chains: "
                f"{', '.join(orphans['cmd_without_chain'][:12])}"
                f"{'…' if len(orphans['cmd_without_chain']) > 12 else ''}"
            )
        if orphans["chain_without_cmd"]:
            _eprint(
                f"  • ключи chains без commands/<stem>.md: "
                f"{', '.join(orphans['chain_without_cmd'][:12])}"
                f"{'…' if len(orphans['chain_without_cmd']) > 12 else ''}"
            )
        if orphans["agent_not_in_registry"]:
            _eprint(
                f"  • agent refs ∉ registry: "
                f"{', '.join(orphans['agent_not_in_registry'][:12])}"
                f"{'…' if len(orphans['agent_not_in_registry']) > 12 else ''}"
            )
        return {"ok": False, "checks": checks, "orphans": orphans}

    _eprint(
        f"✅ COMMAND CHAINS GATE PASS — "
        f"{checks['chain_keys']} keys ↔ {checks['commands_on_disk']} commands; "
        f"agent_refs={checks['agent_refs']}"
    )
    return {"ok": True, "checks": checks, "orphans": orphans}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plugin-root", type=Path, default=Path("."))
    ap.add_argument(
        "--warn-soft",
        action="store_true",
        help="WARN на stderr если registry agent не referenced в chains (exit 0)",
    )
    args = ap.parse_args()
    root = args.plugin_root.expanduser().resolve()

    result = run_gate(root, warn_soft=args.warn_soft)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
