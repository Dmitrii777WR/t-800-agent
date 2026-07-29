#!/usr/bin/env python3
"""t800_loop_hitl_approve.py — HITL marker for auto-LOW batch.

Creates/removes {memory}/.loop-auto-low-approved.
Does NOT flip loop-policy.json auto_low.enabled (manual).

Usage:
  python3 scripts/t800_loop_hitl_approve.py --memory-path PATH --auto-low
  python3 scripts/t800_loop_hitl_approve.py --memory-path PATH --auto-low --revoke

Exit: 0 pass, 1 fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HITL_REL = ".loop-auto-low-approved"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="T-800 HITL approve for auto-LOW")
    parser.add_argument("--memory-path", required=True)
    parser.add_argument(
        "--auto-low",
        action="store_true",
        help="Surface: auto-LOW HITL file (required in v1)",
    )
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Удалить HITL-файл",
    )
    args = parser.parse_args()

    if not args.auto_low:
        print(
            "FAIL: нужен флаг --auto-low (v1 поддерживает только auto-LOW surface)",
            file=sys.stderr,
        )
        return 1

    memory_path = Path(args.memory_path).expanduser().resolve()
    hitl_path = memory_path / HITL_REL
    summary: dict[str, Any] = {
        "ok": True,
        "memory_path": str(memory_path),
        "path": str(hitl_path),
        "error": None,
    }

    try:
        memory_path.mkdir(parents=True, exist_ok=True)
        if args.revoke:
            if hitl_path.is_file():
                hitl_path.unlink()
            summary["revoked"] = True
            summary["approved"] = False
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        payload = {
            "approved_at": utc_now(),
            "by": "hitl",
            "purpose": "auto_low",
        }
        hitl_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summary["approved"] = True
        summary["revoked"] = False
        summary["payload"] = payload
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except OSError as exc:
        summary["ok"] = False
        summary["error"] = str(exc)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
