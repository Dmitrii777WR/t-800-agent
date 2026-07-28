# Fix-pack — обязательные секции

Шаблон: `templates/fix-pack.md.template`.  
Путь: `{memory_path}/fix-packs/<slug>.md`.

| Секция | Назначение |
|--------|------------|
| `goal` | Зачем правка (1–3 предложения) |
| `surface` | cursor-plugin / workspace / user |
| `files[]` | Точные пути PATCH (whitelist) |
| `changes[]` | Что сделать в каждом файле |
| `constraints` | Что нельзя трогать |
| `research_mode` | skip \| light \| deep |
| `success_criteria` | Как понять PASS |

## Источники pack

- Ручной draft по audit
- `scripts/t800_audit_to_fixpack.py`
- `scripts/t800_lessons_to_fixpack.py` (из loop-queue, status=open)

Без `files[]` — **blocked**, не угадывать scope.
