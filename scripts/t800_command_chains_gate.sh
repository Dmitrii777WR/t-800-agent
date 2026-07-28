#!/usr/bin/env bash
# Thin wrapper → t800_command_chains_gate.py (same dir)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/t800_command_chains_gate.py" "$@"
