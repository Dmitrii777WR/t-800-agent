# Discovery-профиль: teya-plugin-dev

> Это **discovery-профиль** (machine SoT для `scripts/discover-target-project.sh`).
> `profiles/beginner-profiles.md` — другой вид профилей (роли новичков для tone-of-voice), не discovery.

Workspace разработки плагина teya (git checkout): сам workspace — plugin_root,
память `plugin-memory/`, маркеры — манифест плагина + продуктовые gate-скрипты.

```json
{
  "id": "teya-plugin-dev",
  "adapter": "teya",
  "markers": {
    "memory_dir_present": "plugin-memory",
    "require": [".cursor-plugin/plugin.json", "plugin-memory/"],
    "any_of": ["scripts/teya_plugin_root.py", "scripts/teya_docs_build.py"]
  },
  "memory_dir": "plugin-memory",
  "slug": "teya",
  "artifact_surface": "cursor-plugin",
  "release_handoff": "/teya-release-sync",
  "plugin_root": {
    "env_key": null,
    "env_file": null,
    "readonly_fallback": null,
    "never_canonical": []
  }
}
```

## Семантика полей

| Поле | Значение |
|------|----------|
| `markers.require` | Оба пути обязаны: манифест `.cursor-plugin/plugin.json` + каталог `plugin-memory/` |
| `markers.any_of` | Хотя бы один продуктовый gate-скрипт: `teya_plugin_root.py` или `teya_docs_build.py` |
| `plugin_root.* = null` | Стратегия «workspace self»: plugin_root = сам workspace (`plugin_root_source: "workspace"`) |
| `release_handoff` | `/teya-release-sync` выполняется в этом же workspace вне T-800 |

Adapter: `adapters/teya/` (matcher `adapters/teya/profiles.py`).
