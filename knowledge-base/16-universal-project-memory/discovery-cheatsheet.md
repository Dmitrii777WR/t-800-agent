---
provenance: manual
author: t-800-factory
---
# Discovery — шпаргалка

```bash
bash scripts/discover-target-project.sh --workspace "."
bash scripts/init-project-memory.sh --workspace "." --slug my-plugin
```

| profile | memory | plugin_root |
|---------|--------|-------------|
| declared adapter (клиент) | memory_dir из `profiles/*.md` | env_key / fallback из профиля |
| declared adapter (dev) | memory_dir из `profiles/*.md` | workspace |
| generic-plugin | {slug}-memory/ | workspace |
| self-t800 | t-800-memory/ | t-800-agent/ |

Если `needs_user_question: true` — спросить путь plugin_root один раз.
