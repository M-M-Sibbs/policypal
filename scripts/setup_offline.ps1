$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { throw "Python 3.11+ is required." }
if ($py -eq "py") { & py -3.11 -m venv .venv } else { & python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-lite.txt
Get-Content .env.offline | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object { $k,$v=$_.Split('=',2); [Environment]::SetEnvironmentVariable($k,$v,'Process') }
& .\.venv\Scripts\python.exe -m app.ingest
& .\.venv\Scripts\python.exe scripts\verify_project.py
Write-Host "`nOffline setup complete. Run: .\scripts\run_offline.ps1"
