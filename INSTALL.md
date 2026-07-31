# T-800 Agent — установка

**Текущая версия:** см. `.cursor-plugin/plugin.json` · **42** core-субагента (+ adapter brains в `adapters/`) · **18** команд

## Установка / обновление

```bash
git clone https://github.com/Khar-AG/t-800-agent.git   # или git pull для обновления
cd t-800-agent
bash scripts/install-plugin.sh
bash scripts/verify-install.sh
```

Ожидайте: `verification passed`. Затем **Developer: Reload Window**.

Сценарий первого старта: [`docs/СЦЕНАРИЙ-СТАРТА.md`](docs/СЦЕНАРИЙ-СТАРТА.md) · обновление со старой версии: [`docs/ОБНОВЛЕНИЕ.md`](docs/ОБНОВЛЕНИЕ.md)

## Команды

| Команда | Зачем |
|---------|--------|
| `/t800-start` | Создать артефакт через полный конвейер отделов (discovery → research → brain → factory → gates) |
| `/t-800` | Алиас `/t800-start` |
| `/t800-fix` | Правка по fix-pack (research SKIP/LIGHT, factory PATCH только файлов из pack) |
| `/t800-loop` | Закрытие прогона: report/lessons → loop-queue (semi-manual) |
| `/t800-doctor` | Здоровье системы / плагина (scripts-only) |
| `/t800-plugin-audit` | Карта одного плагина: inventory/graph/orphans → fix-pack |
| `/t800-audit` | Bloat-аудит всей системы Cursor (rules/skills) |
| `/t800-bootstrap` | Первый запуск: аудит + глобальное правило по согласию |
| `/t800-onboard` | Онбординг: аудит global/local Cursor + возможности T-800 |
| `/t800-cloud-hub` | Cloud Hub / Client Automation Setup (лид + специалисты) |
| `/t800-hub-setup` | Алиас `/t800-cloud-hub` |
| `/t800-update` | Ручное обновление с GitHub (scripts-only) |
| `/t-800-factory` | Прямой запуск конвейера, когда brain-контекст уже готов |
| `/t-800-sync` | Sync базы знаний KB |
| `/t-800-maintain` | Maintainer-обслуживание KB |
| `/t-800-operator` | Обучение новичков (только когда пользователь просит) |
| `/t-800-health` | Агрегированный health-check (scripts-only) |
| `/t-800-factory-validate` | Валидация агентов и графа связей |

## Тесты

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Windows

- Hooks (`hooks/*.sh`) — **bash-only** (Git Bash / WSL).
- ps1-пары: `install-plugin`, `verify-install`, `validate-agents`, `audit-agent-graph`, `audit-coverage`, `health-check`, `t800-loop-dispatcher`, `discover-target-project`, `t800_command_chains_gate`.
- Ограничение: `t800_loop_state.sh` — только bash (Git Bash / WSL).
- Gates `scripts/*.py` — кросс-платформенны (python3).
