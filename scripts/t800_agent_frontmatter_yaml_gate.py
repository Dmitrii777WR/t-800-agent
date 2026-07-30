#!/usr/bin/env python3
"""FAIL если frontmatter agents/*.md или commands/*.md не парсится PyYAML.

Cursor выкидывает агентов с битым YAML из Task enum (Invalid enum).
Agents: обязательны name, description (str), model: inherit.
Commands: если есть --- frontmatter — обязателен description (валидный YAML); без FM (legacy T-800) — skip, не FAIL.

Антипаттерн (incident hybrid): description: "…" затем hanging
Use when / Do NOT / indented continuation до следующего ключа → FAIL.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("❌ AGENT FRONTMATTER YAML GATE FAIL — нужен PyYAML (pip install pyyaml)")
    sys.exit(1)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Next top-level frontmatter key after description (agents/commands)
NEXT_KEY_RE = re.compile(
    r"^(?:model|readonly|is_background|name|description|color|temperature|"
    r"isBackground|tools)\s*:",
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
    """Detect description: \"…\" then hanging indented / Use|Do NOT lines.

    Even if a lenient parser swallowed the block, this pattern is banned.
    """
    errors: list[str] = []
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match description: "..." or description: '...' on one line (closed quotes)
        m = re.match(
            r'^description:\s*(["\'])(.*)\1\s*$',
            line,
        )
        if not m:
            i += 1
            continue
        # Closed quoted scalar on description line — peek following lines
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                j += 1
                continue
            if NEXT_KEY_RE.match(nxt):
                break
            # Indented continuation or Use/Do NOT after closed quotes = hybrid
            if nxt.startswith((" ", "\t")) or HYBRID_HANGING_RE.match(nxt):
                errors.append(
                    f"{rel}: hybrid description — закрытые кавычки на "
                    f"description, затем hanging строка {j + 1!r}: {nxt.strip()[:80]!r}. "
                    "Emit ONLY description: > fold ИЛИ one-line quoted без продолжений."
                )
                break
            # Non-indented garbage before next key
            if not NEXT_KEY_RE.match(nxt):
                errors.append(
                    f"{rel}: после description: \"…\" неожиданная строка "
                    f"{j + 1}: {nxt.strip()[:80]!r}"
                )
                break
            break
        i += 1
    return errors


def check_agents(agents_dir: Path) -> list[str]:
    errors: list[str] = []
    if not agents_dir.is_dir():
        return [f"нет каталога agents: {agents_dir}"]
    for path in sorted(agents_dir.glob("*.md")):
        rel = f"agents/{path.name}"
        data, err, raw = _load_frontmatter(path)
        if err:
            errors.append(f"{rel}: {err}")
            if raw is not None:
                errors.extend(_hybrid_quoted_hanging_errors(raw, rel))
            continue
        assert data is not None and raw is not None
        errors.extend(_hybrid_quoted_hanging_errors(raw, rel))
        if not data.get("name"):
            errors.append(f"{rel}: нет name")
        desc = data.get("description")
        if not desc or not isinstance(desc, str) or not desc.strip():
            errors.append(f"{rel}: нет description (строка)")
        model = data.get("model")
        if model != "inherit":
            errors.append(f"{rel}: model должен быть inherit, сейчас {model!r}")
    return errors


def check_commands(commands_dir: Path) -> list[str]:
    """Validate commands that have YAML frontmatter.

    Legacy T-800 commands without ``---`` FM are skipped (not FAIL):
    Cursor Invalid enum incident targets agents; adding FM to all
    commands is a separate migration outside this gate's FAIL set.
    If frontmatter exists — same strict rules as adapter plugins (description str).
    """
    errors: list[str] = []
    if not commands_dir.is_dir():
        return [f"нет каталога commands: {commands_dir}"]
    for path in sorted(commands_dir.glob("*.md")):
        rel = f"commands/{path.name}"
        text = path.read_text(encoding="utf-8")
        if not FRONTMATTER_RE.match(text):
            # Legacy: no YAML frontmatter — skip (do not FAIL plugin scan)
            continue
        data, err, raw = _load_frontmatter(path)
        if err:
            errors.append(f"{rel}: {err}")
            if raw is not None:
                errors.extend(_hybrid_quoted_hanging_errors(raw, rel))
            continue
        assert data is not None and raw is not None
        errors.extend(_hybrid_quoted_hanging_errors(raw, rel))
        desc = data.get("description")
        if not desc or not isinstance(desc, str) or not desc.strip():
            errors.append(f"{rel}: нет description (строка)")
    return errors


def check_paths(paths: list[Path]) -> list[str]:
    """Check arbitrary md paths (fixtures / single files)."""
    errors: list[str] = []
    for path in paths:
        if not path.is_file():
            errors.append(f"нет файла: {path}")
            continue
        rel = str(path)
        data, err, raw = _load_frontmatter(path)
        if err:
            errors.append(f"{rel}: {err}")
            if raw is not None:
                errors.extend(_hybrid_quoted_hanging_errors(raw, rel))
            continue
        assert data is not None and raw is not None
        errors.extend(_hybrid_quoted_hanging_errors(raw, rel))
        desc = data.get("description")
        if not desc or not isinstance(desc, str) or not desc.strip():
            errors.append(f"{rel}: нет description (строка)")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plugin-root", type=Path, default=Path("."))
    ap.add_argument(
        "--file",
        action="append",
        type=Path,
        default=[],
        help="Проверить один или несколько md (fixtures); иначе agents+commands",
    )
    args = ap.parse_args()
    root = args.plugin_root.resolve()

    if args.file:
        errors = check_paths([p.expanduser().resolve() for p in args.file])
        n_agents, n_cmds = 0, 0
        label = f"{len(args.file)} file(s)"
    else:
        errors = check_agents(root / "agents") + check_commands(root / "commands")
        n_agents = (
            len(list((root / "agents").glob("*.md")))
            if (root / "agents").is_dir()
            else 0
        )
        n_cmds = (
            len(list((root / "commands").glob("*.md")))
            if (root / "commands").is_dir()
            else 0
        )
        label = f"{n_agents} agents + {n_cmds} commands"

    if errors:
        print("❌ AGENT FRONTMATTER YAML GATE FAIL")
        for e in errors:
            print(f"  • {e}")
        print(f"Проверено: {label}; FAIL={len(errors)}")
        return 1

    print(
        f"✅ AGENT FRONTMATTER YAML GATE PASS — {label} "
        f"(PyYAML ok; agents: name+description+model inherit; no hybrid)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
