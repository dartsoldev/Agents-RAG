# Purpose: start the API, browser frontend and embedded workflow worker on the same local port.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { throw 'Run .\scripts\setup.ps1 first.' }
& '.\.venv\Scripts\python.exe' -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
Write-Host 'Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.' -ForegroundColor Green
& '.\.venv\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
