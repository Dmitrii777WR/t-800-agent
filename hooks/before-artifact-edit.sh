#!/usr/bin/env bash
# preToolUse (T-800) — policy modes: observe | warn | enforce
# Default: enforce (deny artifact edits outside factory). Opt-out:
#   T800_HOOK_MODE=warn|observe  or  T800_TEYA_HOOK_MODE=warn|observe
# Sibling Teya checkout paths are NOT memory SoT.
set -u

payload=$(cat 2>/dev/null || true)

# Mode: observe | warn | enforce (default enforce since 1.22.0)
HOOK_MODE="${T800_TEYA_HOOK_MODE:-${T800_HOOK_MODE:-enforce}}"
HOOK_MODE=$(printf '%s' "$HOOK_MODE" | tr '[:upper:]' '[:lower:]')
case "$HOOK_MODE" in
  observe|warn|enforce) ;;
  *) HOOK_MODE="enforce" ;;
esac

json_escape() {
  local msg="${1:-}"
  msg=${msg//\\/\\\\}
  msg=${msg//\"/\\\"}
  msg=${msg//$'\n'/\\n}
  printf '%s' "$msg"
}

allow() {
  printf '{"permission":"allow"}'
  exit 0
}

warn_allow() {
  local msg
  msg=$(json_escape "${1:-}")
  printf '{"permission":"allow","user_message":"%s","agent_message":"%s"}' "$msg" "$msg"
  exit 0
}

deny() {
  local msg
  msg=$(json_escape "${1:-}")
  printf '{"permission":"deny","user_message":"%s","agent_message":"%s"}' "$msg" "$msg"
  exit 0
}

# Bypass: активный factory run
if [[ -n "${T800_FACTORY_RUN_ID:-}" ]]; then
  allow
fi

# preToolUse вход: tool_input.file_path → tool_input.path →
# tool_input.target_notebook → legacy top-level filePath → path; пусто = allow (fail-open)
edited_path=""
edited_path=$(printf '%s' "$payload" | sed -n 's/.*"tool_input"[[:space:]]*:[[:space:]]*{[^{}]*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
if [[ -z "$edited_path" ]]; then
  edited_path=$(printf '%s' "$payload" | sed -n 's/.*"tool_input"[[:space:]]*:[[:space:]]*{[^{}]*"path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
fi
if [[ -z "$edited_path" ]]; then
  edited_path=$(printf '%s' "$payload" | sed -n 's/.*"tool_input"[[:space:]]*:[[:space:]]*{[^{}]*"target_notebook"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
fi
if [[ -z "$edited_path" ]]; then
  edited_path=$(printf '%s' "$payload" | sed -n 's/.*"filePath"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
fi
if [[ -z "$edited_path" ]]; then
  edited_path=$(printf '%s' "$payload" | sed -n 's/.*"path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
fi

if [[ -z "${edited_path}" ]]; then
  allow
fi

norm=${edited_path//\\//}

is_artifact=0
case "$norm" in
  */agents/*.md|*/agents/*/*.md|agents/*.md)
    is_artifact=1
    ;;
  */commands/*.md|commands/*.md|*/.cursor/commands/*.md)
    is_artifact=1
    ;;
  */skills/*/SKILL.md|skills/*/SKILL.md|*/.cursor/skills/*/SKILL.md)
    is_artifact=1
    ;;
  */rules/*.mdc|rules/*.mdc|*/.cursor/rules/*.mdc)
    is_artifact=1
    ;;
  */hooks.json|hooks.json|*/hooks/*.sh|hooks/*.sh|*/hooks/*.ps1|hooks/*.ps1)
    is_artifact=1
    ;;
esac

base=$(basename "$norm")
dir=$(dirname "$norm")
dir_base=$(basename "$dir")
if [[ "$is_artifact" -eq 0 ]]; then
  case "$dir_base/$base" in
    agents/*.md|commands/*.md|rules/*.mdc)
      is_artifact=1
      ;;
  esac
  if [[ "$base" == "SKILL.md" && "$dir_base" != "." ]]; then
    case "$norm" in
      *skills*|*/.cursor/skills/*) is_artifact=1 ;;
    esac
  fi
  if [[ "$base" == "hooks.json" ]]; then
    is_artifact=1
  fi
fi

if [[ "$is_artifact" -eq 0 ]]; then
  allow
fi

# Soft bypass: discovered memory / env — NEVER sibling ../TeyaPlugin as SoT
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || HERE="."
PLUGIN_ROOT="$(cd "$HERE/.." 2>/dev/null && pwd)" || PLUGIN_ROOT=""

factory_in_manifest() {
  local man="$1"
  [[ -f "$man" ]] || return 1
  # in_progress markers only — NOT completed/ok/done
  if grep -Eqi '"agent"[[:space:]]*:[[:space:]]*"t-800-factory"' "$man" 2>/dev/null \
    && grep -Eqi '"status"[[:space:]]*:[[:space:]]*"(in_progress|running|started|active)"' "$man" 2>/dev/null; then
    return 0
  fi
  if grep -Eqi '"factory"[[:space:]]*:[[:space:]]*"(in_progress|running|started|active)"' "$man" 2>/dev/null; then
    return 0
  fi
  return 1
}

for mem in \
  "${T800_MEMORY_PATH:-}" \
  "./plugin-memory" \
  "./t-800-memory" \
  "${PLUGIN_ROOT}/../t-800-memory"
do
  [[ -z "$mem" ]] && continue
  if factory_in_manifest "${mem}/run-manifest.json"; then
    allow
  fi
done

# Optional: discovery memory_path (best-effort, no sibling TeyaPlugin)
if [[ -x "${PLUGIN_ROOT}/scripts/discover-target-project.sh" ]]; then
  disc=$(bash "${PLUGIN_ROOT}/scripts/discover-target-project.sh" --workspace "." 2>/dev/null || true)
  mem_from_disc=$(printf '%s' "$disc" | sed -n 's/.*"memory_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  if [[ -n "$mem_from_disc" ]] && factory_in_manifest "${mem_from_disc}/run-manifest.json"; then
    allow
  fi
fi

MSG_WARN="T-800 WARN: правка Cursor-артефакта (${base}) без T800_FACTORY_RUN_ID / factory в run-manifest. Используйте /t800-start или /t800-fix → Task(t-800-factory). Gate: t800_factory_bypass_gate.py. mode=${HOOK_MODE}"

MSG_DENY="T-800 DENY: правка Cursor-артефакта (${base}) вне factory run. Используйте /t800-start или /t800-fix → Task(t-800-factory). Opt-out: T800_HOOK_MODE=warn|observe (или T800_TEYA_HOOK_MODE). Bypass: T800_FACTORY_RUN_ID / factory in_progress в run-manifest."

case "$HOOK_MODE" in
  observe)
    allow
    ;;
  warn)
    warn_allow "$MSG_WARN"
    ;;
  *)
    deny "$MSG_DENY"
    ;;
esac
