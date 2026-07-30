#!/usr/bin/env bash
# discover-target-project.sh — универсальное обнаружение plugin_root и memory_path
# Product-специфика декларативна: profiles/<id>.md (ОДИН fenced ```json блок — SoT маркеров).
# Ядро детектит: marker → profiles loop → self-t800 → generic-plugin → workspace-cursor.
set -euo pipefail

WORKSPACE="."
PLUGIN_ROOT_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="$2"; shift 2 ;;
    --plugin-root) PLUGIN_ROOT_OVERRIDE="$2"; shift 2 ;;
    *) WORKSPACE="$1"; shift ;;
  esac
done

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILES_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/profiles"

needs_user_question=false
profile="unknown"
profile_declared=false
plugin_root=""
memory_dir=""
memory_path=""
slug=""
release_handoff="null"
knowledge_vault_path="null"
plugin_json=""
artifact_surface="cursor-workspace"
plugin_root_source="null"
write_allowed=true
adapter="null"

# --- Discovery-профили (profiles/<id>.md, один fenced json блок) ------------

profile_block() { # profile_block <id> → raw json блок или пусто
  local f="$PROFILES_DIR/$1.md"
  [[ -f "$f" ]] || return 1
  awk '/^```json$/{f=1;next} /^```$/{if(f)exit} f' "$f"
}

profile_field() { # profile_field <json> <field-expr на d>
  python3 -c "import json,sys
d=json.loads(sys.argv[1])
$2" "$1" 2>/dev/null
}

# Совпадение workspace ↔ profiles/*.md по markers {require[], any_of[], memory_dir_present}
match_profiles() { # match_profiles <workspace> → compact json совпавшего профиля
  local ws="$1" f pid block compact
  for f in "$PROFILES_DIR"/*.md; do
    [[ -f "$f" ]] || continue
    pid="$(basename "$f" .md)"
    block="$(awk '/^```json$/{f=1;next} /^```$/{if(f)exit} f' "$f")"
    [[ -n "$block" ]] || continue
    compact="$(python3 -c "import json,sys
try:
    d=json.loads(sys.argv[1])
except Exception:
    sys.exit(1)
m=d.get('markers') or {}
ws=sys.argv[2]
def ok(rel): return os.path.exists(os.path.join(ws, rel))
import os
req=m.get('require') or []
if any(not ok(r) for r in req): sys.exit(1)
ao=m.get('any_of') or []
if ao and not any(ok(a) for a in ao): sys.exit(1)
mem=m.get('memory_dir_present')
if mem and not os.path.isdir(os.path.join(ws, mem)): sys.exit(1)
d['id']=d.get('id') or sys.argv[3]
print(json.dumps(d, separators=(',', ':')))" "$block" "$ws" "$pid" 2>/dev/null)" || continue
    [[ -n "$compact" ]] || continue
    printf '%s' "$compact"
    return 0
  done
  return 0
}

# plugin_root из профиля: env_key (grep env_file) → readonly_fallback → workspace self
resolve_profile_plugin_root() { # resolve_profile_plugin_root <json>
  local pj="$1" env_key env_file fallback val fb
  env_key="$(profile_field "$pj" "print((d.get('plugin_root') or {}).get('env_key') or '')")"
  env_file="$(profile_field "$pj" "print((d.get('plugin_root') or {}).get('env_file') or '')")"
  fallback="$(profile_field "$pj" "print((d.get('plugin_root') or {}).get('readonly_fallback') or '')")"
  if [[ -n "$env_key" ]]; then
    val="${!env_key:-}"
    if [[ -z "$val" && -n "$env_file" ]]; then
      env_file="${env_file/#\~/$HOME}"
      if [[ -f "$env_file" ]]; then
        val="$(grep -E "^${env_key}=" "$env_file" | tail -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
      fi
    fi
    if [[ -n "$val" && -d "$val" ]]; then
      plugin_root="$(cd "$val" && pwd)"
      plugin_root_source="\"env\""
      write_allowed=true
      return 0
    fi
  fi
  if [[ -n "$fallback" ]]; then
    fb="${fallback/#\~/$HOME}"
    if [[ -d "$fb" ]]; then
      # Readonly fallback для чтения контрактов — не write destination
      plugin_root="$(cd "$fb" && pwd)"
      plugin_root_source="\"installed_readonly\""
      write_allowed=false
      needs_user_question=true
      return 0
    fi
  fi
  if [[ -z "$env_key" && -z "$fallback" ]]; then
    # Стратегия «workspace self»: профиль без env/fallback — плагин = сам workspace
    plugin_root="$WORKSPACE"
    plugin_root_source="\"workspace\""
    write_allowed=true
    return 0
  fi
  return 1
}

# 1) project-memory.marker.json (walk up)
search="$WORKSPACE"
while [[ "$search" != "/" ]]; do
  marker="$search/project-memory.marker.json"
  if [[ -f "$marker" ]]; then
    slug="$(python3 -c "import json; d=json.load(open('$marker')); print(d.get('slug',''))" 2>/dev/null || echo "")"
    memory_dir="$(python3 -c "import json; d=json.load(open('$marker')); print(d.get('memory_dir',''))" 2>/dev/null || echo "")"
    pr="$(python3 -c "import json; d=json.load(open('$marker')); print(d.get('plugin_root','.'))" 2>/dev/null || echo ".")"
    rh="$(python3 -c "import json; d=json.load(open('$marker')); print(d.get('release_handoff') or '')" 2>/dev/null || echo "")"
    if [[ -n "$rh" ]]; then release_handoff="\"$rh\""; fi
    kvp="$(python3 -c "import json; d=json.load(open('$marker')); v=d.get('knowledge_vault_path'); print(v if isinstance(v,str) and v.strip() else '')" 2>/dev/null || echo "")"
    if [[ -n "$kvp" ]]; then
      knowledge_vault_path="\"$(python3 -c "from pathlib import Path; p=Path('''$kvp'''); print(p if p.is_absolute() else (Path('''$search''')/p).resolve())" 2>/dev/null || echo "$kvp")\""
    fi
    if [[ "$pr" == "." ]]; then
      plugin_root="$search"
    else
      plugin_root="$(cd "$search/$pr" && pwd)"
    fi
    memory_path="$search/$memory_dir"
    # Product override внутри marker: marker + memory манифеста + .cursor-plugin + product gates
    # → профиль из profiles/ (adapter читается из совпавшего профиля, не хардкод)
    if [[ -d "$search/plugin-memory" ]] && [[ -f "$search/.cursor-plugin/plugin.json" ]]; then
      mo="$(match_profiles "$search")"
      if [[ -n "$mo" ]]; then
        profile="$(profile_field "$mo" "print(d.get('id') or '')")"
        profile_declared=true
        artifact_surface="$(profile_field "$mo" "print(d.get('artifact_surface') or 'cursor-plugin')")"
        slug="${slug:-$(profile_field "$mo" "print(d.get('slug') or '')")}"
        if [[ "$release_handoff" == "null" ]]; then
          mrh="$(profile_field "$mo" "print(d.get('release_handoff') or '')")"
          if [[ -n "$mrh" ]]; then release_handoff="\"$mrh\""; fi
        fi
      else
        profile="marker"
      fi
    else
      profile="marker"
    fi
    break
  fi
  search="$(dirname "$search")"
done

# 2) Profiles loop: product-профили из profiles/*.md (declared markers)
if [[ "$profile" == "unknown" ]]; then
  pm="$(match_profiles "$WORKSPACE")"
  if [[ -n "$pm" ]]; then
    profile="$(profile_field "$pm" "print(d.get('id') or '')")"
    profile_declared=true
    memory_dir="$(profile_field "$pm" "print(d.get('memory_dir') or '')")"
    memory_path="$WORKSPACE/$memory_dir"
    slug="$(profile_field "$pm" "print(d.get('slug') or '')")"
    artifact_surface="$(profile_field "$pm" "print(d.get('artifact_surface') or 'cursor-plugin')")"
    prh="$(profile_field "$pm" "print(d.get('release_handoff') or '')")"
    if [[ -n "$prh" ]]; then release_handoff="\"$prh\""; fi
    resolve_profile_plugin_root "$pm" || true
    # Optional KVP from marker without overriding profile (если шаг 1 не сработал)
    if [[ "$knowledge_vault_path" == "null" ]] && [[ -f "$WORKSPACE/project-memory.marker.json" ]]; then
      kvp="$(python3 -c "import json; d=json.load(open('$WORKSPACE/project-memory.marker.json')); v=d.get('knowledge_vault_path'); print(v if isinstance(v,str) and v.strip() else '')" 2>/dev/null || echo "")"
      if [[ -n "$kvp" ]]; then
        knowledge_vault_path="\"$(python3 -c "from pathlib import Path; p=Path('''$kvp'''); print(p if p.is_absolute() else (Path('''$WORKSPACE''')/p).resolve())" 2>/dev/null || echo "$kvp")\""
      fi
    fi
    # never_canonical из профиля — информационные заметки: sibling-пути никогда не canonical,
    # discovery их не угадывает (plugin_root только env / readonly fallback / workspace self).
  fi
fi

# 3) Self T-800
if [[ -z "$memory_dir" ]] && [[ -d "$WORKSPACE/t-800-memory" ]] && [[ -d "$WORKSPACE/t-800-agent/.cursor-plugin" ]]; then
  profile="self-t800"
  plugin_root="$WORKSPACE/t-800-agent"
  artifact_surface="cursor-plugin"
  memory_dir="t-800-memory"
  memory_path="$WORKSPACE/t-800-memory"
  slug="t-800-agent"
fi

# 4) Generic: .cursor-plugin + {name}-memory
if [[ -z "$plugin_root" ]] && [[ -f "$WORKSPACE/.cursor-plugin/plugin.json" ]]; then
  plugin_json="$WORKSPACE/.cursor-plugin/plugin.json"
  pname="$(python3 -c "import json; print(json.load(open('$plugin_json')).get('name','plugin'))" 2>/dev/null || echo "plugin")"
  slug="$pname"
  plugin_root="$WORKSPACE"
  candidate="${pname}-memory"
  if [[ -d "$WORKSPACE/$candidate" ]]; then
    memory_dir="$candidate"
    memory_path="$WORKSPACE/$candidate"
    profile="generic-plugin"
    artifact_surface="cursor-plugin"
  else
    profile="generic-plugin"
    artifact_surface="cursor-plugin"
    memory_dir="$candidate"
    memory_path="$WORKSPACE/$candidate"
    needs_user_question=true
  fi
fi

# 5) t-800-agent inside workspace only
if [[ -z "$plugin_root" ]] && [[ -d "$WORKSPACE/t-800-agent/.cursor-plugin" ]]; then
  profile="self-t800"
  plugin_root="$WORKSPACE/t-800-agent"
  artifact_surface="cursor-plugin"
  if [[ -d "$WORKSPACE/t-800-memory" ]]; then
    memory_dir="t-800-memory"
    memory_path="$WORKSPACE/t-800-memory"
  elif [[ -d "$WORKSPACE/t-800-agent/t-800-memory" ]]; then
    memory_dir="t-800-memory"
    memory_path="$WORKSPACE/t-800-agent/t-800-memory"
  else
    memory_dir="t-800-memory"
    memory_path="$WORKSPACE/t-800-memory"
    needs_user_question=true
  fi
  slug="t-800-agent"
  artifact_surface="cursor-plugin"
fi

# 6) Workspace — skills/rules в .cursor/ (не плагин)
if [[ "$profile" == "unknown" ]] && [[ -z "$plugin_root" ]]; then
  if [[ -d "$WORKSPACE/.cursor" ]] || [[ -d "$WORKSPACE/.git" ]]; then
    profile="workspace-cursor"
    artifact_surface="cursor-workspace"
    memory_dir=".cursor/t800-memory"
    memory_path="$WORKSPACE/.cursor/t800-memory"
    slug="workspace"
    mkdir -p "$memory_path/fragments" "$memory_path/factory-briefs" 2>/dev/null || true
  fi
fi

# Неразрешённый plugin_root: declared product-профиль сохраняет identity,
# остальные без памяти → unknown; workspace-cursor не флагается здесь.
if [[ -z "$plugin_root" ]] && [[ "$profile" != "workspace-cursor" ]]; then
  needs_user_question=true
  if [[ -z "$memory_dir" ]] && [[ "$profile_declared" != "true" ]]; then
    profile="unknown"
  fi
fi

if [[ -n "$memory_dir" ]] && [[ ! -d "$memory_path" ]]; then
  needs_user_question=true
fi

# Явный выбор оператора (--plugin-root после list-target-plugins)
if [[ -n "$PLUGIN_ROOT_OVERRIDE" ]] && [[ -d "$PLUGIN_ROOT_OVERRIDE/.cursor-plugin" ]]; then
  plugin_root="$(cd "$PLUGIN_ROOT_OVERRIDE" && pwd)"
  needs_user_question=false
  if [[ "$profile" == "unknown" ]]; then
    profile="generic-plugin"
    artifact_surface="cursor-plugin"
  fi
  if [[ -f "$plugin_root/.cursor-plugin/plugin.json" ]]; then
    slug="$(python3 -c "import json; print(json.load(open('$plugin_root/.cursor-plugin/plugin.json')).get('name','plugin'))" 2>/dev/null || echo "$slug")"
  fi
fi

# Default sources
if [[ "$plugin_root_source" == "null" ]] && [[ -n "${plugin_root:-}" ]]; then
  if [[ "$profile_declared" == "true" ]]; then
    plugin_root_source="\"workspace\""
  elif [[ "$profile" == "marker" ]]; then
    plugin_root_source="\"marker\""
  elif [[ -n "$PLUGIN_ROOT_OVERRIDE" ]]; then
    plugin_root_source="\"override\""
  else
    plugin_root_source="\"discovery\""
  fi
fi

# Adapter из совпавшего discovery-профиля (profiles/<id>.md → поле adapter)
if [[ "$adapter" == "null" ]] && [[ "$profile" != "unknown" ]]; then
  pb="$(profile_block "$profile" 2>/dev/null || true)"
  if [[ -n "$pb" ]]; then
    av="$(profile_field "$pb" "print(d.get('adapter') or '')")"
    if [[ -n "$av" ]]; then adapter="\"$av\""; fi
  fi
fi

cat <<EOF
{
  "workspace_root": "$WORKSPACE",
  "plugin_root": "${plugin_root:-}",
  "plugin_root_source": $plugin_root_source,
  "write_allowed": $write_allowed,
  "memory_dir": "${memory_dir:-}",
  "memory_path": "${memory_path:-}",
  "profile": "$profile",
  "slug": "${slug:-}",
  "artifact_surface": "$artifact_surface",
  "release_handoff": $release_handoff,
  "knowledge_vault_path": $knowledge_vault_path,
  "adapter": $adapter,
  "needs_user_question": $needs_user_question
}
EOF
