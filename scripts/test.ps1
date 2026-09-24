# Purpose: run isolated automated workflow and security regression tests.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
& '.\.venv\Scripts\python.exe' -m pytest -q
exit $LASTEXITCODE
