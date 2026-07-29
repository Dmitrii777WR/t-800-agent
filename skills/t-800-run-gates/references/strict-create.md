# --strict-create

На CREATE (`/t800-start`, factory CREATE) перед «готово»:

При `--strict-create` + `--plugin-root` auto-ON: agents-mirror, kb-provenance, frontmatter-yaml, skill-frontmatter, plugin-json-schema, command-chains.

```bash
python3 scripts/t800_run_gate.py --strict-create \
  --memory-path "<memory_path>" \
  --plugin-root "<plugin_root>" \
  [--factory-brief "<slug>"]
```

Флаги вручную: `--require-agents-mirror`, `--require-kb-provenance`, `--require-frontmatter-yaml`, …

## Обычно требует

1. Manifest / run-manifest фиксирует factory stage.
2. Fragment factory (или auditor) со `status: ok` / PASS.
3. Brief `factory-briefs/<slug>.yaml` в состоянии done / закрыт по контракту.
4. Нет open blockers в STATE, блокирующих сдачу.

## FAIL примеры

- CREATE без factory fragment
- Brief не done, а директор объявил готово
- Silent skip `--strict-create`

PATCH идёт без `--strict-create`, но с обычным `t800_run_gate.py` + scope pack.

Контракт: `shared/loop-engineering-contract.md`, `shared/plan-to-factory-handoff-contract.md`.
