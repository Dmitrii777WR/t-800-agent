# Discovery-профиль: teya-client

> Это **discovery-профиль** (machine SoT для `scripts/discover-target-project.sh`).
> `profiles/beginner-profiles.md` — другой вид профилей (роли новичков для tone-of-voice), не discovery.

Клиентский workspace адаптера teya: память `teya-memory/` в клиенте, plugin_root
резолвится из env `TEYA_PLUGIN_ROOT` (git checkout), installed-копия — только readonly.

```json
{
  "id": "teya-client",
  "adapter": "teya",
  "markers": {
    "memory_dir_present": "teya-memory",
    "require": [],
    "any_of": []
  },
  "memory_dir": "teya-memory",
  "slug": "teya",
  "artifact_surface": "cursor-plugin",
  "release_handoff": "/teya-release-sync",
  "plugin_root": {
    "env_key": "TEYA_PLUGIN_ROOT",
    "env_file": "~/.teya/teya.env.global",
    "readonly_fallback": "~/.cursor/plugins/local/teya",
    "never_canonical": ["../TeyaPlugin", "../../TeyaPlugin"]
  }
}
```

## Семантика полей

| Поле | Значение |
|------|----------|
| `markers.memory_dir_present` | Каталог `teya-memory/` в workspace — единственный маркер детекта |
| `plugin_root.env_key` / `env_file` | Сначала env `TEYA_PLUGIN_ROOT`; если пуст — grep ключа из `env_file` (без source файла секретов) |
| `plugin_root.readonly_fallback` | Installed-копия: `write_allowed=false`, `needs_user_question=true`, только чтение контрактов |
| `plugin_root.never_canonical` | Sibling `../TeyaPlugin` — никогда не canonical SoT (информационная заметка для операторов, discovery не угадывает sibling) |
| `release_handoff` | Handoff оператору: открыть git checkout плагина → `/teya-release-sync` (T-800 не выполняет release sync) |

Adapter: `adapters/teya/` (matcher `adapters/teya/profiles.py`).
