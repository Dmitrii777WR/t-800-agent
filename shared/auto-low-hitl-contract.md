# Auto-LOW HITL Contract (v1.0)

Контракт пакетной генерации LOW fix-packs **только после HITL**.  
Не вызывает factory. Не stop/followup Ralph. Не LLM `risk_class`.

Связано: `shared/loop-engineering-contract.md`, `shared/lesson-schema-contract.md`,
`shared/fix-pipeline-contract.md`.

## Цель

После явного HITL-approve создать черновики fix-packs из open LOW lessons  
и передать человека на `/t800-fix` — **без** автозапуска factory.

## Policy (`loop-policy.json`)

```json
"auto_low": {
  "enabled": false,
  "require_hitl_file": ".loop-auto-low-approved",
  "daily_budget": 3,
  "max_per_batch": 3
}
```

| Ключ | Default | Смысл |
|------|---------|--------|
| `enabled` | **false** | OFF в template; включать руками |
| `require_hitl_file` | `.loop-auto-low-approved` | файл в `{memory}/` |
| `daily_budget` | 3 | apply-события за сегодня UTC |
| `max_per_batch` | 3 | потолок packs за один batch |

## HITL-файл

Путь: `{memory_path}/.loop-auto-low-approved`

```json
{
  "approved_at": "2026-07-29T12:00:00Z",
  "by": "hitl",
  "purpose": "auto_low"
}
```

### CLI approve / revoke

```bash
python3 scripts/t800_loop_hitl_approve.py --memory-path PATH --auto-low
python3 scripts/t800_loop_hitl_approve.py --memory-path PATH --auto-low --revoke
```

Approve **не** ставит `enabled: true` — это отдельный ручной шаг в policy.

## Batch CLI

```bash
# default = dry-run
python3 scripts/t800_auto_low_batch.py --memory-path PATH [--lessons PATH|run_id]

# записать packs
python3 scripts/t800_auto_low_batch.py --memory-path PATH --lessons … --apply
```

### Gates (FAIL exit 1)

1. Существует `{memory}/.loop-paused`
2. Нет `{memory}/loop-policy.json`
3. `auto_low.enabled != true`
4. Нет HITL-файла
5. `daily_budget` исчерпан (лог `{memory}/telemetry/auto-low-log.jsonl`, actions `apply`|`batch_apply`, дата UTC today)

### Поведение

- Подпроцесс: `t800_lessons_to_fixpack.py` (только packs)
- **Запрет:** factory / `T800_FACTORY_RUN_ID` / Task(t-800-factory)
- `--apply` → append log `action=batch_apply`
- dry-run **не** пишет log и **не** создаёт packs
- stdout: `{ ok, mode, created, next: ["/t800-fix"], packs, budget_remaining }`

## Anti-list

- stop + followup / subagentStop followup как движок цикла  
- LLM назначает `risk_class: LOW`  
- auto-LOW без HITL-файла  
- batch вызывает factory  

## Версия

- Введён: 2026-07-29 · T-800 **1.22.0**
