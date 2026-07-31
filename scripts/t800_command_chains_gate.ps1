# t800_command_chains_gate.ps1 - pwsh wrapper for t800_command_chains_gate.py (parity with .sh)
# Usage: pwsh scripts/t800_command_chains_gate.ps1 [same args as .py, e.g. --plugin-root PATH]

python3 "$PSScriptRoot/t800_command_chains_gate.py" @args
exit $LASTEXITCODE
