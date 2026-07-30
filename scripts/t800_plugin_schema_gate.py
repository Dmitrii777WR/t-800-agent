#!/usr/bin/env python3
"""Validate .cursor-plugin/plugin.json vs registry/plugin.manifest.schema.json.

- python3 + jsonschema (NO Node/AJV)
- required: name
- displayName allowed (schema additionalProperties / explicit property)
- relative paths rules|skills|agents|commands|hooks must exist on disk
- FAIL: missing name, schema errors, broken paths
- if jsonschema missing: clear RU error + exit 1

CLI: --plugin-root PATH [--json]
stdout: OK/FAIL (+ JSON optional); exit 0/1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover
    print(
        "❌ PLUGIN SCHEMA GATE FAIL — нужен пакет jsonschema "
        "(pip install jsonschema)",
        file=sys.stderr,
    )
    sys.exit(1)

PATH_KEYS = ("rules", "skills", "agents", "commands", "hooks")


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_manifest_path(plugin_root: Path, rel: str) -> Path:
    cleaned = rel.strip()
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return (plugin_root / cleaned).resolve()


def check_plugin(plugin_root: Path) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {
        "manifest": ".cursor-plugin/plugin.json",
        "schema": "registry/plugin.manifest.schema.json",
        "name": None,
        "paths_checked": [],
    }

    manifest_path = plugin_root / ".cursor-plugin" / "plugin.json"
    schema_path = plugin_root / "registry" / "plugin.manifest.schema.json"

    if not manifest_path.is_file():
        errors.append(f"нет файла {manifest_path.relative_to(plugin_root)}")
        return False, errors, meta
    if not schema_path.is_file():
        errors.append(f"нет schema {schema_path.relative_to(plugin_root)}")
        return False, errors, meta

    try:
        manifest = _load_json(manifest_path)
        schema = _load_json(schema_path)
    except json.JSONDecodeError as exc:
        errors.append(f"JSON parse FAIL: {exc}")
        return False, errors, meta
    except OSError as exc:
        errors.append(f"read FAIL: {exc}")
        return False, errors, meta

    if not isinstance(manifest, dict):
        errors.append("plugin.json: корень не object")
        return False, errors, meta

    name = manifest.get("name")
    meta["name"] = name
    if not name or not isinstance(name, str) or not str(name).strip():
        errors.append("plugin.json: отсутствует обязательное поле name")

    # jsonschema validate (keeps displayName via additionalProperties / property)
    try:
        validator = Draft7Validator(schema)
        for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.path)):
            loc = ".".join(str(p) for p in err.path) or "(root)"
            errors.append(f"schema [{loc}]: {err.message}")
    except jsonschema.exceptions.SchemaError as exc:
        errors.append(f"сама schema невалидна: {exc}")

    for key in PATH_KEYS:
        val = manifest.get(key)
        if val is None:
            continue
        if not isinstance(val, str) or not val.strip():
            errors.append(f"plugin.json.{key}: ожидается непустая строка пути")
            continue
        target = _resolve_manifest_path(plugin_root, val)
        meta["paths_checked"].append({"key": key, "path": val, "exists": target.exists()})
        if not target.exists():
            errors.append(
                f"plugin.json.{key}={val!r} → путь не существует: {target}"
            )

    return len(errors) == 0, errors, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plugin-root", type=Path, default=Path("."))
    ap.add_argument("--json", action="store_true", help="Stdout JSON summary")
    args = ap.parse_args()
    root = args.plugin_root.expanduser().resolve()

    ok, errors, meta = check_plugin(root)

    if args.json:
        print(
            json.dumps(
                {"ok": ok, "errors": errors, "meta": meta},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif ok:
        print(
            f"✅ PLUGIN SCHEMA GATE PASS — name={meta.get('name')!r}; "
            f"paths ok; displayName allowed"
        )
    else:
        print("❌ PLUGIN SCHEMA GATE FAIL")
        for e in errors:
            print(f"  • {e}")
        _eprint(f"FAIL={len(errors)}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
