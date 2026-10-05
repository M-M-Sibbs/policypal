$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path .\.venv\Scripts\python.exe)) { throw "Run .\scripts\setup_offline.ps1 first." }
Get-Content .env.offline | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object { $k,$v=$_.Split('=',2); [Environment]::SetEnvironmentVariable($k,$v,'Process') }
if (-not (Test-Path .\storage\chroma-offline\index_meta.json)) { & .\.venv\Scripts\python.exe -m app.ingest }
& .\.venv\Scripts\python.exe -m flask --app app run --host 127.0.0.1 --port 5000
