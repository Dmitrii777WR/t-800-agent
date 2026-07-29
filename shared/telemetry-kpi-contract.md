# Telemetry KPI Contract (schema 1.1)

Контракт KPI-полей в append-only JSONL телеметрии T-800.  
Скрипт: `scripts/t800_telemetry.py`. Связано: `shared/loop-engineering-contract.md`.

## Schema

| Поле | Тип | Обязательность | Правило |
|------|-----|----------------|---------|
| `schema_version` | string | auto | `"1.1"` (setdefault при append) |
| `ts` | string ISO-UTC | auto | setdefault при append |
| `duration_ms` | int ≥ 0 | optional | если присутствует — только int ≥ 0 |
| `tokens_in` | int ≥ 0 | optional | если присутствует — только int ≥ 0 |
| `tokens_out` | int ≥ 0 | optional | если присутствует — только int ≥ 0 |
| `retries` | int ≥ 0 | optional | если присутствует — только int ≥ 0 |
| `run_id` | string | optional | id прогона |
| `stage` | string | optional | отдел / этап (для `by_stage`) |
| `status` | string | optional | pass\|fail\|partial\|… |
| `event` | string | optional | тип события (`run_report`, `run_complete`, `usage_ingest`, …) |
| `source` | string | optional | для ingest: `ui_or_env` |

**Append-only:** события schema 1.0 без KPI остаются валидными. Негативные / не-int KPI → `ValueError` / exit 1.

## Usage ingest (1.22.0)

Мост ручного ввода из Cursor Usage UI / env → тот же JSONL.

| | |
|--|--|
| Script | `scripts/t800_usage_ingest.py` |
| Template | `templates/usage-draft.json.template` |
| Event | `event=usage_ingest`, `source=ui_or_env` |
| Path | `{memory_path}/telemetry/runs.jsonl` |

**Merge (низкий → высокий приоритет):** empty → `--from-env` → `--from-file` → CLI flags.

Env (`--from-env`): `T800_USAGE_TOKENS_IN`, `T800_USAGE_TOKENS_OUT`, `T800_USAGE_DURATION_MS`, `T800_USAGE_RUN_ID`.

Нужно хотя бы одно из: `tokens_in` / `tokens_out` / `duration_ms`.

```bash
python3 scripts/t800_usage_ingest.py --memory-path PATH --tokens-in 10 --tokens-out 20
python3 scripts/t800_usage_ingest.py --memory-path PATH --from-env
python3 scripts/t800_usage_ingest.py --memory-path PATH --from-file usage-draft.json
```

## Пути

| Ключ | Путь |
|------|------|
| jsonl | `{memory_path}/telemetry/runs.jsonl` |
| summary | `{memory_path}/telemetry/summary.json` |

## CLI

```bash
# append
python3 scripts/t800_telemetry.py --memory-path PATH --event '{"duration_ms":120,"retries":0}'

# summarize (exit 0 даже при missing KPI)
python3 scripts/t800_telemetry.py --memory-path PATH --summarize

# strict: >50% событий без duration_ms → exit 1
python3 scripts/t800_telemetry.py --memory-path PATH --summarize --strict-kpi
```

## Summary JSON

```json
{
  "count": 3,
  "count_missing_kpi": 0,
  "duration_ms": {"sum": 600, "avg": 200.0, "p50": 200.0, "n": 3},
  "tokens": {"in": 90, "out": 120},
  "retries": {"sum": 3, "avg": 1.0, "n": 3},
  "by_stage": {"factory": 1, "research": 1, "brain": 1}
}
```

- `count_missing_kpi` — число событий **без** `duration_ms`.
- `avg` / `p50` считаются только по событиям с `duration_ms`.
- Без `--strict-kpi` missing KPI не FAIL.

## Интеграция

`t800_run_report.py` передаёт в telemetry optional `--duration-ms` и `--retries` (default 0).

## Версия

- Обновлён: 2026-07-29 · T-800 **1.22.0** (usage ingest)
- Введён: 2026-07-29 · T-800 **1.21.1** · schema **1.1**
