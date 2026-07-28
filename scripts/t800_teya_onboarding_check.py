#!/usr/bin/env python3
"""t800_teya_onboarding_check.py — readonly Teya onboarding checklist (Phase 1).

Does NOT mutate rollout_state, release, HITL, or green streak.

Usage:
  python3 scripts/t800_teya_onboarding_check.py \\
    --plugin-root PATH --memory-path PATH --handoff PATH \\
    [--profile teya-plugin-dev]

Exit 0 = checklist ok (or skip non-teya).
Exit 1 = onboarding gaps.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from adapters.teya.handoff import load_handoff  # noqa: E402
from adapters.teya.profiles import is_teya_profile  # noqa: E402

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    data: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            data[key] = val
    return data


def _check_agent(plugin_root: Path, agent_id: str, handoff: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    path = plugin_root / "agents" / f"{agent_id}.md"
    exists = path.is_file()
    checks.append({"id": "file_exists", "ok": exists, "path": str(path.relative_to(plugin_root)) if exists else str(path)})
    if not exists:
        return checks

    text = path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    checks.append({"id": "frontmatter_valid", "ok": bool(fm and fm.get("name")), "detail": fm})

    depts = _load_json(plugin_root / "shared" / "agent-departments.json")
    in_dept = False
    if isinstance(depts, dict):
        # common shapes: {departments: {name: {agents: []}}} or agents map
        blob = json.dumps(depts, ensure_ascii=False)
        in_dept = agent_id in blob
    required = "department_required" in (handoff.get("requested_capabilities") or []) or handoff.get(
        "department_required"
    )
    checks.append(
        {
            "id": "department_membership",
            "ok": in_dept or bool(required),
            "in_registry": in_dept,
            "explicit_required": bool(required),
        }
    )

    cap_reg = _load_json(plugin_root / "shared" / "capability-registry.json")
    in_cap = False
    if isinstance(cap_reg, dict):
        agents = cap_reg.get("agents") or {}
        if isinstance(agents, dict):
            in_cap = agent_id in agents
        elif isinstance(agents, list):
            in_cap = any(
                (isinstance(a, dict) and a.get("id") == agent_id) or a == agent_id for a in agents
            )
    cap_required = bool(handoff.get("requested_capabilities")) or handoff.get("capability_required")
    checks.append(
        {
            "id": "capability_mapping",
            "ok": in_cap or bool(cap_required),
            "in_registry": in_cap,
            "explicit_required": bool(cap_required),
        }
    )

    mirror = plugin_root / ".cursor" / "agents" / f"{agent_id}.md"
    mirror_needed = (plugin_root / ".cursor" / "agents").is_dir()
    checks.append(
        {
            "id": "mirror_requirement",
            "ok": (not mirror_needed) or mirror.is_file() or path.is_file(),
            "mirror_exists": mirror.is_file(),
        }
    )

    # duplicate by filename only (simple)
    dup = list((plugin_root / "agents").glob(f"**/{agent_id}.md"))
    checks.append({"id": "duplicate_conflict", "ok": len(dup) <= 1, "count": len(dup)})
    return checks


def _command_stem(cmd: str) -> str:
    c = cmd.strip().lstrip("/")
    if c.endswith(".md"):
        c = c[:-3]
    return c


def _check_command(plugin_root: Path, command: str, handoff: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    stem = _command_stem(command)
    path = plugin_root / "commands" / f"{stem}.md"
    exists = path.is_file()
    checks.append({"id": "command_file", "ok": exists, "stem": stem})

    chains = _load_json(plugin_root / "shared" / "command-chains.json")
    in_chains = False
    if isinstance(chains, dict):
        cmds = chains.get("commands") or chains
        if isinstance(cmds, dict):
            in_chains = stem in cmds or f"/{stem}" in cmds
        elif isinstance(cmds, list):
            in_chains = stem in cmds
    checks.append({"id": "command_chains", "ok": in_chains})

    intent_py = plugin_root / "scripts" / "teya_intent_router.py"
    intent_ok = False
    if intent_py.is_file():
        text = intent_py.read_text(encoding="utf-8", errors="replace")
        intent_ok = stem in text or f"/{stem}" in text
    intent_required = bool(handoff.get("intent_required"))
    checks.append(
        {
            "id": "intent_mapping",
            "ok": intent_ok or intent_required,
            "in_router": intent_ok,
            "explicit_required": intent_required,
        }
    )

    profile_path = plugin_root / "shared" / "command-profiles" / f"{stem}.json"
    profile = _load_json(profile_path) if profile_path.is_file() else None
    checks.append({"id": "command_profile", "ok": isinstance(profile, dict), "path": str(profile_path.name)})

    owner_ok = False
    rollout = None
    if isinstance(profile, dict):
        owner_ok = bool(
            profile.get("owner")
            or profile.get("owner_manager")
            or profile.get("required_capabilities")
            or profile.get("gates")
            or profile.get("gate_profiles")
        )
        rollout = profile.get("rollout_state")
    checks.append({"id": "owner_caps_gates", "ok": owner_ok or not isinstance(profile, dict)})

    allowed_rollout = {None, "", "shadow", "disabled"}
    rollout_ok = rollout in allowed_rollout or str(rollout).lower() in allowed_rollout
    if str(rollout).lower() in {"canary", "enforced", "guarded"}:
        # For brand-new from factory, ceiling is shadow — FAIL if higher
        if handoff.get("artifact_type") in {"command", "bundle"} and handoff.get("status") in {
            "factory_complete",
            "onboarding_required",
        }:
            # Only enforce ceiling when handoff marks command as new_stub
            if handoff.get("new_command_stub", True):
                rollout_ok = False
    checks.append(
        {
            "id": "rollout_ceiling",
            "ok": rollout_ok,
            "rollout_state": rollout,
            "note": "new stubs must not exceed shadow",
        }
    )

    readiness = None
    if isinstance(profile, dict):
        readiness = profile.get("readiness_status") or profile.get("readiness")
    readiness_ok = readiness in {
        None,
        "",
        "not_ready",
        "onboarding_required",
    } or str(readiness).lower() in {"not_ready", "onboarding_required"}
    checks.append({"id": "readiness_default", "ok": readiness_ok, "readiness": readiness})

    fixtures = handoff.get("expected_fixtures") or []
    gates = handoff.get("expected_gates") or []
    listed = bool(fixtures or gates) or handoff.get("artifact_type") != "command"
    checks.append({"id": "fixtures_listed", "ok": listed, "fixtures": fixtures, "gates": gates})
    return checks


def run_check(
    *,
    plugin_root: Path,
    memory_path: Path,
    handoff: dict[str, Any],
    profile: str,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "ok": True,
        "profile": profile,
        "plugin_root": str(plugin_root),
        "memory_path": str(memory_path),
        "run_id": handoff.get("run_id"),
        "status": handoff.get("status"),
        "checks": [],
        "errors": [],
    }

    if not is_teya_profile(profile):
        summary["ok"] = False
        summary["errors"].append("adapter_requires_teya_profile")
        return summary

    root_s = str(plugin_root.resolve()).replace("\\", "/")
    if "/.cursor/plugins/local/teya" in root_s:
        summary["ok"] = False
        summary["errors"].append("write_target_is_installed_local_teya")

    for agent_id in handoff.get("expected_agents") or []:
        for c in _check_agent(plugin_root, agent_id, handoff):
            c["target"] = agent_id
            c["kind"] = "agent"
            summary["checks"].append(c)
            if not c.get("ok"):
                summary["errors"].append(f"agent:{agent_id}:{c['id']}")

    for cmd in handoff.get("expected_commands") or []:
        for c in _check_command(plugin_root, cmd, handoff):
            c["target"] = cmd
            c["kind"] = "command"
            summary["checks"].append(c)
            if not c.get("ok"):
                summary["errors"].append(f"command:{cmd}:{c['id']}")

    # capability / risk / gate entries when requested
    for cap in handoff.get("requested_capabilities") or []:
        if cap in {"department_required", "capability_required"}:
            continue
        reg = _load_json(plugin_root / "shared" / "capability-registry.json")
        present = False
        if isinstance(reg, dict):
            caps = reg.get("capabilities") or {}
            if isinstance(caps, dict):
                present = cap in caps
            elif isinstance(caps, list):
                present = any(
                    (isinstance(x, dict) and x.get("capability_id") == cap) or x == cap for x in caps
                )
        ok = present or handoff.get("capability_registration_required") is True
        # If explicit list given, require present unless marked required-for-later
        if handoff.get("capability_registration_required"):
            ok = present
        summary["checks"].append(
            {"id": "capability_registry_entry", "kind": "capability", "target": cap, "ok": present or not handoff.get("capability_registration_required"), "present": present}
        )
        if handoff.get("capability_registration_required") and not present:
            summary["errors"].append(f"capability_missing:{cap}")

    for risk in handoff.get("requested_risk_effects") or []:
        reg = _load_json(plugin_root / "shared" / "risk-registry.json")
        present = False
        if isinstance(reg, dict):
            risks = reg.get("risks") or []
            if isinstance(risks, list):
                present = any(
                    (isinstance(x, dict) and x.get("risk_id") == risk) or x == risk for x in risks
                )
            elif isinstance(risks, dict):
                present = risk in risks
        if handoff.get("risk_registration_required") and not present:
            summary["errors"].append(f"risk_missing:{risk}")
        summary["checks"].append(
            {"id": "risk_registry_entry", "kind": "risk", "target": risk, "ok": present or not handoff.get("risk_registration_required"), "present": present}
        )

    for fx in handoff.get("expected_fixtures") or []:
        p = plugin_root / fx if not Path(fx).is_absolute() else Path(fx)
        # also allow relative to tests/
        alt = plugin_root / "tests" / fx
        ok = p.is_file() or p.is_dir() or alt.is_file() or alt.is_dir()
        summary["checks"].append({"id": "fixture_exists", "kind": "fixture", "target": fx, "ok": ok})
        if not ok and handoff.get("require_fixtures", False):
            summary["errors"].append(f"fixture_missing:{fx}")

    # provenance
    if not handoff.get("factory_brief_id") or not handoff.get("run_id"):
        summary["errors"].append("provenance_incomplete")
    summary["checks"].append(
        {
            "id": "provenance_link",
            "ok": bool(handoff.get("factory_brief_id") and handoff.get("run_id")),
            "factory_brief_id": handoff.get("factory_brief_id"),
            "run_id": handoff.get("run_id"),
        }
    )

    summary["ok"] = len(summary["errors"]) == 0
    summary["verdict"] = "onboarding_pass" if summary["ok"] else "onboarding_blocked"
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Readonly Teya onboarding checklist")
    ap.add_argument("--plugin-root", required=True)
    ap.add_argument("--memory-path", required=True)
    ap.add_argument("--handoff", required=True, help="Path to factory-handoffs/<run-id>.json")
    ap.add_argument("--profile", default="")
    args = ap.parse_args()

    plugin_root = Path(args.plugin_root).resolve()
    memory_path = Path(args.memory_path).resolve()
    handoff = load_handoff(args.handoff)
    profile = args.profile or str(handoff.get("target_profile") or "")

    if not is_teya_profile(profile):
        out = {
            "ok": False,
            "skipped": False,
            "error": "not_a_teya_profile",
            "profile": profile,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1

    summary = run_check(
        plugin_root=plugin_root,
        memory_path=memory_path,
        handoff=handoff,
        profile=profile,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
