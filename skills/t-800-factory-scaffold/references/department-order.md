# Department order — кто кого зовёт

Контракт: `shared/department-orchestration-contract.md`.

## CREATE (`/t800-start`)

Директор зовёт **только лидов**. Leaf — авто внутри лида.

```
intake-clarifier?  →  scout  →  research-lead  →  prompt-craft?
       →  brain-lead  →  factory
```

| Отдел | Task | Специалисты |
|-------|------|-------------|
| Intake | `t-800-intake-clarifier` | — |
| Scout | `t-800-scout` | — |
| Research | `t-800-research-lead` | strategist → specialists → synthesizer |
| Craft | `t-800-prompt-craft` | — (agent/skill/command) |
| Brains | `t-800-brain-lead` | 1–2 domain brains |
| Factory | `t-800-factory` | architect → builder → … → auditor |

## Правила

- Не звать builder/github/brain-context из main chat.
- Не плодить новых research/brain агентов без отдельного решения.
- PATCH → `/t800-fix`, не полный DEEP-старт.
