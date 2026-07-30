# Gate matrix

Контракт: `shared/loop-engineering-contract.md`.

| Check | CREATE | PATCH | LOOP | AUDIT/OPS |
|-------|--------|-------|------|-----------|
| `STATE.md` present / Gates section | required | required | required | optional |
| `t800_run_gate.py` | required | required | as contract | — |
| `--strict-create` | required | no | no | no |
| frontmatter YAML gate (agents/commands) | if touched | if touched | — | — |
| future `--require-skills-validate` | when landed | when skills | — | — |
| `t800_factory_bypass_gate.py` | advisory/required per release | same | — | — |
| `t800_prompt_eval_gate.py` | optional / verify-install | optional / verify-install | — | behavioral markers (must_contain) |
| `t800_doctor.py` | optional | optional | — | preferred for /t800-doctor |
| command-chains orphan gate | if chains/cmds | if cmds | — | plugin-audit |

## doctor vs run_gate

- **doctor** — здоровье/отчёт, обычно exit 0 даже при findings.
- **run_gate** — hard PASS/FAIL перед «готово» CREATE/PATCH.

Hooks `preToolUse` (artifact-edit guard) в v1 — WARN, не sole gate.
