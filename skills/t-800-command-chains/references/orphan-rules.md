# Orphan rules

Согласовано с `shared/plugin-audit-contract.md` + будущим `t800_command_chains_gate.py`.

## FAIL (P0)

1. `commands/<stem>.md` есть, ключа нет в `shared/command-chains.json` → `commands{}`.
2. Ключ в chains есть, файла `commands/<stem>.md` нет.
3. `lead` или id в `agents[]` ∉ `registry/agents-registry.json` (если registry present), кроме явного `null` lead.

## WARN (soft, не FAIL P0)

- Агент в registry никогда не referenced в chains / calledBy — informational.
- Soft prose «зови X» в agent body без записи в JSON — не замена machine graph.

## При добавлении команды

1. Создать `commands/<stem>.md` через factory.
2. Добавить ключ в `shared/command-chains.json` (lead/mode/pipeline/agents).
3. Прогнать orphan gate + plugin-audit при необходимости.
4. Не держать «временные» команды без chains-записи.
