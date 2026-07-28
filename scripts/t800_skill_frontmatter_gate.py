#!/usr/bin/env python3
"""FAIL если frontmatter skills/*/SKILL.md нарушает Cursor skill FM rules.

Mirror of t800_agent_frontmatter_yaml_gate.py для skills:

  - required: name (str), description (str)
  - name == parent folder
  - allowlist keys: name, description, paths, disable-model-invocation, metadata
  - forbid: displayName, model, readonly, is_background, tools, alwaysApply, globs
  - hybrid quoted+hanging description → FAIL
  - disable-model-invocation: bool; paths: list[str]; metadata: mapping

CLI: --plugin-root PATH [--json]
stdout: OK/FAIL (или JSON при --json); exit 0/1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("❌ SKILL FRONTMATTER GATE FAIL — нужен PyYAML (pip install pyyaml)")
    sys.exit(1)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

ALLOWLIST = {
    "name",
    "description",
    "paths",
    "disable-model-invocation",
    "metadata",
}

FORBID = {
    "displayName",
    "model",
    "readonly",
    "is_background",
    "isBackground",
    "tools",
    "alwaysApply",
    "globs",
}

NEXT_KEY_RE = re.compile(
    r"^(?:name|description|paths|disable-model-invocation|metadata|"
    r"displayName|model|readonly|is_background|isBackground|tools|"
    r"alwaysApply|globs)\s*:",
    re.IGNORECASE,
)

HYBRID_HANGING_RE = re.compile(
    r"(?i)^\s+(?:Use when|Do NOT(?: use when)?|Lead |Orchestrat|"
    r"Readonly|QA |Промпт|Валидир|Создаёт|Создает)"
)


def _load_frontmatter(path: Path) -> tuple[dict | None, str | None, str | None]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, "нет YAML frontmatter (--- ... ---)", None
    raw = m.group(1)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, f"PyYAML FAIL: {exc}", raw
    if data is None:
        return None, "пустой frontmatter", raw
    if not isinstance(data, dict):
        return None, f"frontmatter не mapping (тип {type(data).__name__})", raw
    return data, None, raw


def _hybrid_quoted_hanging_errors(raw: str, rel: str) -> list[str]:
    errors: list[str] = []
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^description:\s*(["\'])(.*)\1\s*$', line)
        if not m:
            i += 1
            continue
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                j += 1
                continue
            if NEXT_KEY_RE.match(nxt):
                break
            if nxt.startswith((" ", "\t")) or HYBRID_HANGING_RE.match(nxt):
                errors.append(
                    f"{rel}: hybrid description — закрытые кавычки на "
                    f"description, затем hanging строка {j + 1!r}: {nxt.strip()[:80]!r}. "
                    "Emit ONLY description: > fold ИЛИ one-line quoted без продолжений."
                )
                break
            if not NEXT_KEY_RE.match(nxt):
                errors.append(
                    f"{rel}: после description: \"…\" неожиданная строка "
                    f"{j + 1}: {nxt.strip()[:80]!r}"
                )
                break
            break
        i += 1
    return errors


def check_skill(path: Path, folder_name: str) -> list[str]:
    rel = f"skills/{folder_name}/SKILL.md"
    errors: list[str] = []
    data, err, raw = _load_frontmatter(path)
    if err:
        errors.append(f"{rel}: {err}")
        if raw is not None:
            errors.extend(_hybrid_quoted_hanging_errors(raw, rel))
        return errors

    assert data is not None and raw is not None
    errors.extend(_hybrid_quoted_hanging_errors(raw, rel))

    unknown = sorted(k for k in data.keys() if k not in ALLOWLIST)
    for k in unknown:
        # любой ключ вне allowlist — FAIL (forbid + unknown)
        tag = "forbid" if k in FORBID else "не в allowlist"
        errors.append(f"{rel}: ключ {k!r} ({tag})")

    name = data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        errors.append(f"{rel}: нет name (строка)")
    elif name != folder_name:
        errors.append(
            f"{rel}: name {name!r} != folder {folder_name!r}"
        )

    desc = data.get("description")
    if not desc or not isinstance(desc, str) or not desc.strip():
        errors.append(f"{rel}: нет description (строка)")

    if "disable-model-invocation" in data:
        dmi = data["disable-model-invocation"]
        if not isinstance(dmi, bool):
            errors.append(
                f"{rel}: disable-model-invocation должен быть bool, сейчас {type(dmi).__name__}"
            )

    if "paths" in data:
        paths = data["paths"]
        if not isinstance(paths, list) or not all(isinstance(x, str) for x in paths):
            errors.append(f"{rel}: paths должен быть list[str]")

    if "metadata" in data:
        meta = data["metadata"]
        if not isinstance(meta, dict):
            errors.append(f"{rel}: metadata должен быть mapping")

    return errors


def check_skills(skills_dir: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    count = 0
    if not skills_dir.is_dir():
        return [f"нет каталога skills: {skills_dir}"], 0
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        if not skill_md.is_file():
            continue
        count += 1
        folder = skill_md.parent.name
        errors.extend(check_skill(skill_md, folder))
    if count == 0:
        errors.append(f"нет skills/*/SKILL.md в {skills_dir}")
    return errors, count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plugin-root", type=Path, default=Path("."))
    ap.add_argument(
        "--json",
        action="store_true",
        help="Stdout JSON {ok, errors, checked} вместо OK/FAIL текста",
    )
    args = ap.parse_args()
    root = args.plugin_root.expanduser().resolve()

    errors, checked = check_skills(root / "skills")
    ok = len(errors) == 0

    if args.json:
        print(
            json.dumps(
                {"ok": ok, "checked": checked, "errors": errors},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif ok:
        print(
            f"✅ SKILL FRONTMATTER GATE PASS — {checked} skill(s) "
            f"(name+description; allowlist; no hybrid; name==folder)"
        )
    else:
        print("❌ SKILL FRONTMATTER GATE FAIL")
        for e in errors:
            print(f"  • {e}")
        print(f"Проверено: {checked} skill(s); FAIL={len(errors)}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
