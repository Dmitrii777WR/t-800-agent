# CREATE checklist — memory артефакты

После discovery (`memory_path`) убедись / создай через отделы (не руками из main chat):

| Артефакт | Кто | Обязателен |
|----------|-----|------------|
| `STATE.md` | loop scripts / director | да |
| `run-manifest.json` | loop / factory | да на CREATE |
| `fragments/t-800-<agent>.md` | каждый отдел | да по пройденным |
| `factory-briefs/<slug>.yaml` | brain → factory | да перед factory |
| `research-briefs/` | research-lead | DEEP/LIGHT |
| Gates в STATE | run_gate | перед «готово» |

## Минимум перед Task(t-800-factory)

1. `memory_path` известен.
2. Brief с `mode: CREATE`, `plugin_root`, `files`/`skills`/`goal`.
3. Research + brain fragments не `needs_input` (или явно SKIP).
4. Director не пишет agents/skills/commands/rules/hooks сам.

Контракты: `shared/project-memory-contract.md`, `shared/plan-to-factory-handoff-contract.md`.
