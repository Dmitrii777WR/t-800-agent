#!/usr/bin/env bash
# list-target-plugins.sh — известные plugin_root для выбора цели (универсальный отдел)
# Источники: known-plugins registry, declarative profiles/*.md (env_key/env_file),
# workspace marker, workspace .cursor-plugin.
set -euo pipefail

REGISTRY="${T800_KNOWN_PLUGINS:-$HOME/.t800/known-plugins.json}"
WORKSPACE="."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILES_DIR="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd)/profiles"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="$2"; shift 2 ;;
    --registry) REGISTRY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

WORKSPACE="$(cd "$WORKSPACE" && pwd)"

python3 - <<'PY' "$REGISTRY" "$WORKSPACE" "$PROFILES_DIR"
import json, os, re, sys
from pathlib import Path

registry_path, workspace, profiles_dir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
plugins = []

def add_unique(slug, name, root, handoff, source):
    root = str(Path(root).resolve()) if root else ""
    if not root or not Path(root).joinpath(".cursor-plugin", "plugin.json").is_file():
        return
    for p in plugins:
        if p["slug"] == slug or p["plugin_root"] == root:
            return
    plugins.append({
        "slug": slug,
        "display_name": name,
        "plugin_root": root,
        "release_handoff": handoff,
        "source": source,
    })

def read_env_key(env_key, env_file):
    """env var → env_file KEY=... → None"""
    val = os.environ.get(env_key, "").strip()
    if val:
        return val
    if env_file:
        f = Path(env_file).expanduser()
        if f.is_file():
            try:
                for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if line.startswith(env_key + "="):
                        return line.split("=", 1)[1].strip()
            except OSError:
                pass
    return None

# Registry file
if Path(registry_path).is_file():
    try:
        data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
        for item in data.get("plugins", []):
            add_unique(
                item.get("slug", "unknown"),
                item.get("display_name", item.get("slug", "")),
                item.get("plugin_root", ""),
                item.get("release_handoff"),
                "registry",
            )
    except (json.JSONDecodeError, OSError):
        pass

# Declarative profiles (adapters declare env_key/env_file; zero product hardcode)
JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
if profiles_dir.is_dir():
    for md in sorted(profiles_dir.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        m = JSON_BLOCK.search(text)
        if not m:
            continue
        try:
            prof = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        pr = prof.get("plugin_root") or {}
        env_key = pr.get("env_key")
        if not env_key:
            continue
        root = read_env_key(env_key, pr.get("env_file"))
        if root:
            slug = prof.get("adapter") or prof.get("id") or md.stem
            add_unique(
                slug,
                slug,
                root,
                prof.get("release_handoff"),
                f"profile:{prof.get('id', md.stem)}",
            )

# Workspace marker
marker = workspace / "project-memory.marker.json"
if marker.is_file():
    try:
        m = json.loads(marker.read_text(encoding="utf-8"))
        pr = m.get("plugin_root", ".")
        root = workspace if pr == "." else (workspace / pr).resolve()
        add_unique(m.get("slug", "workspace"), m.get("slug", "workspace"), str(root), m.get("release_handoff"), "marker")
    except (json.JSONDecodeError, OSError):
        pass

# Workspace is plugin repo
pj = workspace / ".cursor-plugin" / "plugin.json"
if pj.is_file():
    try:
        name = json.loads(pj.read_text(encoding="utf-8")).get("name", workspace.name)
        add_unique(name, name, str(workspace), None, "workspace")
    except (json.JSONDecodeError, OSError):
        pass

print(json.dumps({"plugins": plugins, "count": len(plugins)}, ensure_ascii=False, indent=2))
PY
