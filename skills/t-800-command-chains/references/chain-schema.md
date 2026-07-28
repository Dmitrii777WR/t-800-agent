# command-chains schema

**SoT:** `shared/command-chains.json`  
Не создавать `registry/command_chains.json`.

## Shape (v1)

```json
{
  "version": 1,
  "meta": {
    "description": "T-800 department command→lead graph",
    "plugin": "t-800-agent"
  },
  "commands": {
    "<stem>": {
      "lead": "t-800-* or null",
      "mode": "CREATE|PATCH|AUDIT|OPS|LOOP|ONBOARD",
      "pipeline": ["ordered", "steps"],
      "agents": ["registry agent ids"],
      "notes": "optional"
    }
  }
}
```

## Правила

- Ключ = stem файла `commands/<stem>.md` (без `.md`).
- `lead` / `agents[]` ids ∈ `registry/agents-registry.json` **или** `lead: null` + `agents: []` для scripts-only.
- `pipeline` — человекочитаемые шаги отдела; не дублировать полный JSON schema в SKILL body.

Gate (когда landed): `scripts/t800_command_chains_gate.py`.
