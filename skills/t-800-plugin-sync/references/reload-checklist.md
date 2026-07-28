# Reload Window checklist

После apply MIR в `~/.cursor/plugins/local/t-800-agent`:

1. Одной строкой: «T-800 обновлён на диске».
2. Попросить пользователя: **Reload Window** (Cursor → Developer / Command Palette).
3. После Reload — продолжить исходную задачу (не сбрасывать контекст без нужды).

## Reload ≠ fix

- Reload подхватывает уже записанные файлы; битый YAML/FM на диске Reload не лечит.
- Hybrid `description: "…"↵  Use when` → silent-drop → Invalid enum. Lesson: `shared/lessons/frontmatter-yaml-silent-drop.md`.
- Если gate FAIL — чинить SoT → sync снова → Reload.

## Авто-update

Hook sessionStart может обновить сам (`shared/auto-update-contract.md`).  
Отключить: `T800_SKIP_AUTO_UPDATE=1`. Ручной: `/t800-update`.
