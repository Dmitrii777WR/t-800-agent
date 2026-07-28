"""Resolve Teya plugin_root without sibling-path as canonical SoT."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


INSTALLED_TEYA = Path.home() / ".cursor" / "plugins" / "local" / "teya"
FORBIDDEN_CANONICAL_PATTERNS = (
    "../TeyaPlugin",
    "../../TeyaPlugin",
)


def _looks_like_teya_checkout(path: Path) -> bool:
    if not path.is_dir():
        return False
    if not (path / ".cursor-plugin" / "plugin.json").is_file():
        return False
    return (path / "scripts" / "teya_plugin_root.py").is_file() or (
        path / "scripts" / "teya_docs_build.py"
    ).is_file()


def _is_installed_local(path: Path) -> bool:
    try:
        return path.resolve() == INSTALLED_TEYA.resolve()
    except OSError:
        return False


def _is_sibling_guess(path: Path, workspace: Path | None) -> bool:
    """True if path equals workspace/../TeyaPlugin or ../../TeyaPlugin."""
    if workspace is None:
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for rel in ("../TeyaPlugin", "../../TeyaPlugin"):
        candidate = (workspace / rel).resolve()
        if candidate == resolved:
            return True
    return False


def resolve_teya_plugin_root(
    *,
    env_root: str | None = None,
    marker_plugin_root: str | None = None,
    workspace: str | Path | None = None,
    discovery_plugin_root: str | None = None,
    allow_installed_readonly: bool = True,
    allow_sibling_canonical: bool = False,
) -> dict[str, Any]:
    """Resolve plugin_root with ordered sources.

    Priority:
      1. TEYA_PLUGIN_ROOT (env)
      2. marker / discovery result (if looks like Teya checkout)
      3. workspace itself (teya-plugin-dev)
      4. installed ~/.cursor/plugins/local/teya as readonly fallback

    Sibling ../TeyaPlugin is NEVER canonical unless allow_sibling_canonical=True
    (tests only; production default False).
    """
    workspace_path = Path(workspace).resolve() if workspace else None
    env_root = env_root if env_root is not None else os.environ.get("TEYA_PLUGIN_ROOT")

    result: dict[str, Any] = {
        "plugin_root": None,
        "plugin_root_source": None,
        "write_allowed": False,
        "canonical": False,
        "needs_user_question": False,
        "rejected_sibling": False,
        "notes": [],
    }

    def accept(path: Path, source: str, *, write: bool, canonical: bool) -> dict[str, Any]:
        result["plugin_root"] = str(path.resolve())
        result["plugin_root_source"] = source
        result["write_allowed"] = write and not _is_installed_local(path)
        result["canonical"] = canonical and not _is_installed_local(path)
        if _is_installed_local(path):
            result["write_allowed"] = False
            result["canonical"] = False
            result["notes"].append("installed_local_readonly")
        return result

    # 1) Env
    if env_root and Path(env_root).is_dir():
        p = Path(env_root)
        if _looks_like_teya_checkout(p) or p.is_dir():
            if _is_sibling_guess(p, workspace_path) and not allow_sibling_canonical:
                # Env pointing at sibling is ok if explicitly set — but mark note
                result["notes"].append("env_equals_sibling_layout")
            return accept(p, "env", write=True, canonical=True)

    # 2) Discovery / marker explicit root
    for raw, source in (
        (discovery_plugin_root, "discovery"),
        (marker_plugin_root, "marker"),
    ):
        if not raw:
            continue
        p = Path(raw)
        if not p.is_dir():
            continue
        if _is_sibling_guess(p, workspace_path) and not allow_sibling_canonical:
            result["rejected_sibling"] = True
            result["notes"].append(f"rejected_sibling_from_{source}")
            continue
        if _looks_like_teya_checkout(p):
            return accept(p, source, write=True, canonical=True)

    # 3) Workspace is TeyaPlugin itself
    if workspace_path and _looks_like_teya_checkout(workspace_path):
        return accept(workspace_path, "workspace", write=True, canonical=True)

    # Explicitly reject naive sibling as canonical
    if workspace_path and not allow_sibling_canonical:
        for rel in FORBIDDEN_CANONICAL_PATTERNS:
            sib = (workspace_path / rel).resolve()
            if _looks_like_teya_checkout(sib):
                result["rejected_sibling"] = True
                result["notes"].append(f"sibling_present_not_canonical:{rel}")

    # 4) Installed readonly fallback
    if allow_installed_readonly and _looks_like_teya_checkout(INSTALLED_TEYA):
        accept(INSTALLED_TEYA, "installed_readonly", write=False, canonical=False)
        result["needs_user_question"] = True
        result["notes"].append("set_TEYA_PLUGIN_ROOT_for_writes")
        return result

    result["needs_user_question"] = True
    result["notes"].append("unresolved")
    return result


def assert_not_sibling_canonical(
    plugin_root: str | Path,
    workspace: str | Path,
) -> dict[str, Any]:
    """FAIL helper for fixtures: sibling must not be treated as canonical."""
    root = Path(plugin_root)
    ws = Path(workspace)
    is_sib = _is_sibling_guess(root, ws)
    return {
        "ok": not is_sib,
        "is_sibling": is_sib,
        "plugin_root": str(root),
        "workspace": str(ws),
        "error": "sibling_path_not_canonical" if is_sib else None,
    }
