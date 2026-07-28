#!/usr/bin/env python3
"""Phase 1 Teya Adapter fixtures — PASS/FAIL + profile matching.

Run from plugin root:
  python3 tests/test_teya_adapter_phase1.py
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
sys.path.insert(0, str(ROOT))

from adapters.teya.discovery import assert_not_sibling_canonical, resolve_teya_plugin_root
from adapters.teya.handoff import build_handoff, validate_handoff_for_t800_write, write_handoff
from adapters.teya.profiles import is_teya_profile, match_brain_teya

PASS = 0
FAIL = 0
RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        status = "PASS"
    else:
        FAIL += 1
        status = "FAIL"
    RESULTS.append({"name": name, "status": status, "detail": detail})
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def write_tree(base: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def run_py(script: str, args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
    )


def test_profile_matching() -> None:
    for profile in ("teya-plugin-dev", "teya-client", "teya-pro"):
        m = match_brain_teya(profile)
        record(f"brain_teya_activates_{profile}", m["activate"] is True and m["brain"] == "t-800-brain-teya")
    record("brain_teya_skips_generic", match_brain_teya("generic-plugin")["activate"] is False)
    record("is_teya_legacy", is_teya_profile("teya-pro"))
    record("adapter_not_generic", not is_teya_profile("generic-plugin"))
    # target_plugin legacy field
    m = match_brain_teya("unknown", target_plugin="teya-pro")
    record("brain_teya_legacy_target_plugin", m["activate"] is True and m["legacy_alias"] is True)


def test_sibling_not_canonical() -> None:
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "client"
        sib = Path(td) / "TeyaPlugin"
        ws.mkdir()
        (ws / "teya-memory").mkdir()
        sib.mkdir()
        (sib / ".cursor-plugin").mkdir()
        (sib / ".cursor-plugin" / "plugin.json").write_text('{"name":"teya"}', encoding="utf-8")
        (sib / "scripts").mkdir()
        (sib / "scripts" / "teya_plugin_root.py").write_text("# stub\n", encoding="utf-8")

        # Without env — must NOT pick sibling as canonical write root
        res = resolve_teya_plugin_root(workspace=ws, env_root=None, allow_sibling_canonical=False)
        sibling_used = res.get("plugin_root") and Path(res["plugin_root"]).resolve() == sib.resolve()
        record(
            "fail_sibling_not_canonical",
            not sibling_used or res.get("canonical") is False,
            json.dumps({"source": res.get("plugin_root_source"), "rejected": res.get("rejected_sibling")}),
        )
        chk = assert_not_sibling_canonical(sib, ws)
        record("assert_sibling_detected", chk["is_sibling"] is True and chk["ok"] is False)

        # With env — OK
        res2 = resolve_teya_plugin_root(workspace=ws, env_root=str(sib), allow_sibling_canonical=False)
        record("env_teya_root_ok", res2.get("plugin_root_source") == "env" and res2.get("write_allowed") is True)


def test_generic_no_teya_release() -> None:
    """Integrator generic branch must forbid Teya release/smoke, not instruct them."""
    text = (ROOT / "agents" / "t-800-factory-integrator.md").read_text(encoding="utf-8")
    idx = text.find("### generic-plugin")
    teya_idx = text.find("### teya-plugin-dev")
    section = text[idx:teya_idx] if idx >= 0 and teya_idx > idx else ""
    has_forbid = "Запрещено" in section and "teya_plugin_smoke" in section
    # Positive instruction pattern (step to run release) should be absent
    positive = "Handoff: **TeyaPlugin" in section or "Smoke: `teya_plugin_smoke" in section
    record("pass_generic_no_teya_release_steps", has_forbid and not positive)


def test_handoff_status_rules() -> None:
    ok_h = build_handoff(
        run_id="r1",
        factory_brief_id="b1",
        target_profile="teya-plugin-dev",
        target_plugin_root="/tmp/fake-teya",
        artifact_type="command",
        status="onboarding_required",
        files_created=["commands/teya-demo.md"],
    )
    v = validate_handoff_for_t800_write(ok_h)
    record("pass_handoff_onboarding_required", v["ok"] is True)

    try:
        build_handoff(
            run_id="r2",
            factory_brief_id="b1",
            target_profile="teya-plugin-dev",
            target_plugin_root="/tmp/fake",
            artifact_type="command",
            status="released",
        )
        record("fail_t800_cannot_set_released", False, "build_handoff allowed released")
    except ValueError:
        record("fail_t800_cannot_set_released", True)

    bad = dict(ok_h)
    bad["status"] = "onboarding_required"
    bad["rollout_state"] = "canary"
    v2 = validate_handoff_for_t800_write(bad)
    record("fail_t800_cannot_set_canary", v2["ok"] is False)

    bad2 = dict(ok_h)
    bad2["files_created"] = ["/Users/someone/Desktop/secret/agent.md"]
    v3 = validate_handoff_for_t800_write(bad2)
    record("fail_personal_absolute_path", v3["ok"] is False)

    bad3 = dict(ok_h)
    bad3["target_plugin_root"] = str(Path.home() / ".cursor/plugins/local/teya")
    v4 = validate_handoff_for_t800_write(bad3)
    record("fail_installed_local_teya", v4["ok"] is False)


def _mini_teya_command_tree(base: Path, *, with_profile: bool, with_chains: bool, with_intent: bool, rollout: str = "shadow") -> None:
    agent_md = """---
name: teya-demo-agent
description: demo
model: inherit
---
# demo
"""
    cmd_md = """# /teya-demo-cmd
Demo command
"""
    files = {
        ".cursor-plugin/plugin.json": '{"name":"teya","version":"0.0.0"}',
        "scripts/teya_plugin_root.py": "print('ok')\n",
        "agents/teya-demo-agent.md": agent_md,
        ".cursor/agents/teya-demo-agent.md": agent_md,
        "commands/teya-demo-cmd.md": cmd_md,
        "shared/agent-departments.json": json.dumps(
            {"departments": {"orchestration": {"agents": ["teya-demo-agent"]}}}, indent=2
        ),
        "shared/capability-registry.json": json.dumps(
            {
                "capabilities": {"cap.demo": {}},
                "agents": {"teya-demo-agent": {"capabilities": ["cap.demo"]}},
            },
            indent=2,
        ),
        "shared/risk-registry.json": json.dumps({"risks": []}, indent=2),
        "tests/fixtures/demo/.keep": "",
    }
    if with_chains:
        files["shared/command-chains.json"] = json.dumps(
            {"commands": {"teya-demo-cmd": {"steps": []}}}, indent=2
        )
    else:
        files["shared/command-chains.json"] = json.dumps({"commands": {}}, indent=2)
    if with_profile:
        files["shared/command-profiles/teya-demo-cmd.json"] = json.dumps(
            {
                "command": "/teya-demo-cmd",
                "owner_manager": "teya-site-manager",
                "required_capabilities": ["cap.demo"],
                "gates": ["teya_demo_gate"],
                "rollout_state": rollout,
                "readiness_status": "not_ready",
            },
            indent=2,
        )
    if with_intent:
        files["scripts/teya_intent_router.py"] = 'COMMAND_INTENT = {"/teya-demo-cmd": "demo"}\n'
    else:
        files["scripts/teya_intent_router.py"] = "COMMAND_INTENT = {}\n"
    write_tree(base, files)


def test_onboarding_pass_command_agent() -> None:
    with tempfile.TemporaryDirectory() as td:
        plugin = Path(td) / "TeyaPlugin"
        mem = plugin / "plugin-memory"
        mem.mkdir(parents=True)
        _mini_teya_command_tree(plugin, with_profile=True, with_chains=True, with_intent=True)
        handoff = build_handoff(
            run_id="pass-cmd-1",
            factory_brief_id="brief-pass",
            target_profile="teya-plugin-dev",
            target_plugin_root=str(plugin),
            artifact_type="bundle",
            artifact_ids=["teya-demo-agent", "teya-demo-cmd"],
            files_created=[
                "agents/teya-demo-agent.md",
                "commands/teya-demo-cmd.md",
            ],
            expected_agents=["teya-demo-agent"],
            expected_commands=["teya-demo-cmd"],
            expected_gates=["teya_demo_gate"],
            expected_fixtures=["fixtures/demo/.keep"],
            requested_capabilities=["cap.demo"],
            status="onboarding_required",
            release_required=True,
        )
        handoff["new_command_stub"] = True
        path = write_handoff(mem, handoff)
        cp = run_py(
            "t800_teya_onboarding_check.py",
            [
                "--plugin-root",
                str(plugin),
                "--memory-path",
                str(mem),
                "--handoff",
                str(path),
                "--profile",
                "teya-plugin-dev",
            ],
        )
        record("pass_teya_command_onboarding", cp.returncode == 0, cp.stdout[-200:])
        gp = run_py(
            "t800_teya_onboarding_gate.py",
            [
                "--profile",
                "teya-plugin-dev",
                "--plugin-root",
                str(plugin),
                "--memory-path",
                str(mem),
                "--handoff",
                str(path),
            ],
        )
        record("pass_teya_gate_allow", gp.returncode == 0, gp.stderr[-120:] if gp.returncode else "")


def test_fail_missing_profile_chains() -> None:
    with tempfile.TemporaryDirectory() as td:
        plugin = Path(td) / "TeyaPlugin"
        mem = plugin / "plugin-memory"
        mem.mkdir(parents=True)
        _mini_teya_command_tree(plugin, with_profile=False, with_chains=False, with_intent=False)
        handoff = build_handoff(
            run_id="fail-cmd-1",
            factory_brief_id="brief-fail",
            target_profile="teya-plugin-dev",
            target_plugin_root=str(plugin),
            artifact_type="command",
            files_created=["commands/teya-demo-cmd.md"],
            expected_commands=["teya-demo-cmd"],
            expected_gates=["g"],
            expected_fixtures=["fixtures/demo/.keep"],
            status="onboarding_required",
        )
        path = write_handoff(mem, handoff)
        cp = run_py(
            "t800_teya_onboarding_check.py",
            ["--plugin-root", str(plugin), "--memory-path", str(mem), "--handoff", str(path)],
        )
        record("fail_command_without_profile_chains_intent", cp.returncode != 0)


def test_fail_agent_without_dept_cap() -> None:
    with tempfile.TemporaryDirectory() as td:
        plugin = Path(td) / "TeyaPlugin"
        mem = plugin / "plugin-memory"
        mem.mkdir(parents=True)
        write_tree(
            plugin,
            {
                ".cursor-plugin/plugin.json": '{"name":"teya"}',
                "scripts/teya_plugin_root.py": "print(1)\n",
                "agents/orphan-agent.md": "---\nname: orphan-agent\ndescription: x\nmodel: inherit\n---\n",
                "shared/agent-departments.json": '{"departments":{}}',
                "shared/capability-registry.json": '{"capabilities":{},"agents":{}}',
            },
        )
        handoff = build_handoff(
            run_id="fail-agent-1",
            factory_brief_id="b",
            target_profile="teya-plugin-dev",
            target_plugin_root=str(plugin),
            artifact_type="agent",
            files_created=["agents/orphan-agent.md"],
            expected_agents=["orphan-agent"],
            status="onboarding_required",
        )
        # no department_required / capability_required → should fail membership
        path = write_handoff(mem, handoff)
        cp = run_py(
            "t800_teya_onboarding_check.py",
            ["--plugin-root", str(plugin), "--memory-path", str(mem), "--handoff", str(path)],
        )
        record("fail_agent_without_department_capability", cp.returncode != 0)


def test_fail_adapter_on_generic() -> None:
    gp = run_py(
        "t800_teya_onboarding_gate.py",
        [
            "--profile",
            "generic-plugin",
            "--plugin-root",
            str(ROOT),
            "--memory-path",
            str(ROOT),
            "--require-teya",
        ],
    )
    record("fail_adapter_for_generic_profile", gp.returncode != 0)


def test_fail_canary_rollout_stub() -> None:
    with tempfile.TemporaryDirectory() as td:
        plugin = Path(td) / "TeyaPlugin"
        mem = plugin / "plugin-memory"
        mem.mkdir(parents=True)
        _mini_teya_command_tree(
            plugin, with_profile=True, with_chains=True, with_intent=True, rollout="canary"
        )
        handoff = build_handoff(
            run_id="fail-canary",
            factory_brief_id="b",
            target_profile="teya-plugin-dev",
            target_plugin_root=str(plugin),
            artifact_type="command",
            files_created=["commands/teya-demo-cmd.md"],
            expected_commands=["teya-demo-cmd"],
            expected_gates=["g"],
            expected_fixtures=["fixtures/demo/.keep"],
            status="onboarding_required",
        )
        handoff["new_command_stub"] = True
        path = write_handoff(mem, handoff)
        cp = run_py(
            "t800_teya_onboarding_check.py",
            ["--plugin-root", str(plugin), "--memory-path", str(mem), "--handoff", str(path)],
        )
        record("fail_new_stub_canary_rollout", cp.returncode != 0)


def test_profiles_activate_adapter_flags() -> None:
    record("pass_teya_plugin_dev_profile", is_teya_profile("teya-plugin-dev"))
    record("pass_teya_client_profile", is_teya_profile("teya-client"))
    record("pass_legacy_teya_pro_alias", is_teya_profile("teya-pro"))


def test_discover_no_sibling_assignment() -> None:
    """Bash discover must not set plugin_root from sibling when env unset."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "clientproj"
        sib = Path(td) / "TeyaPlugin"
        ws.mkdir()
        (ws / "teya-memory").mkdir()
        sib.mkdir()
        (sib / ".cursor-plugin").mkdir()
        (sib / ".cursor-plugin" / "plugin.json").write_text('{"name":"teya"}', encoding="utf-8")
        (sib / "scripts").mkdir()
        (sib / "scripts" / "teya_plugin_root.py").write_text("print('x')\n", encoding="utf-8")
        env = os.environ.copy()
        env.pop("TEYA_PLUGIN_ROOT", None)
        # prevent reading user global env affecting test — script reads ~/.teya; we can't easily block
        # but sibling must not win over empty: if TEYA from global exists, skip assert
        cp = subprocess.run(
            ["bash", str(ROOT / "scripts" / "discover-target-project.sh"), "--workspace", str(ws)],
            capture_output=True,
            text=True,
            env=env,
        )
        data = json.loads(cp.stdout)
        root = data.get("plugin_root") or ""
        is_sib = root and Path(root).resolve() == sib.resolve()
        source = data.get("plugin_root_source")
        record(
            "discover_sibling_not_assigned_as_canonical",
            (not is_sib) or source == "installed_readonly",
            json.dumps({"plugin_root": root, "source": source, "profile": data.get("profile")}),
        )


def test_hook_no_teya_sibling_literal() -> None:
    hook = (ROOT / "hooks" / "before-artifact-edit.sh").read_text(encoding="utf-8")
    # No path assignment to sibling TeyaPlugin (comment-only mentions also banned for clarity)
    record(
        "hook_no_hardcoded_sibling_teyaplugin",
        "TeyaPlugin/plugin-memory" not in hook and 'PLUGIN_ROOT}/../Teya' not in hook,
    )
    record("hook_has_modes", "enforce" in hook and "warn" in hook and "observe" in hook)


def main() -> int:
    print("=== Teya Adapter Phase 1 fixtures ===")
    test_profile_matching()
    test_profiles_activate_adapter_flags()
    test_sibling_not_canonical()
    test_generic_no_teya_release()
    test_handoff_status_rules()
    test_onboarding_pass_command_agent()
    test_fail_missing_profile_chains()
    test_fail_agent_without_dept_cap()
    test_fail_adapter_on_generic()
    test_fail_canary_rollout_stub()
    test_discover_no_sibling_assignment()
    test_hook_no_teya_sibling_literal()

    summary = {"pass": PASS, "fail": FAIL, "total": PASS + FAIL, "results": RESULTS}
    out = ROOT / "tests" / "fixtures" / "teya-adapter" / "last-run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": PASS, "fail": FAIL, "total": PASS + FAIL}, ensure_ascii=False))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
