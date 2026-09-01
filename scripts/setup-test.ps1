$ErrorActionPreference = "Stop"
python -c "import sys; assert sys.version_info >= (3,11)"
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker daemon is not running." }
if (-not (Test-Path .env.test)) { Copy-Item .env.test.example .env.test }
if (Select-String -Path .env.test -Pattern '^SL_REAL_EMAIL_ENABLED=(true|1|yes)$' -Quiet) { throw "Real email is enabled." }
if (-not (Test-Path .venv)) { python -m venv .venv }
. .venv/Scripts/Activate.ps1
python -m pip install --upgrade pip | Out-Null
python -m pip install -e '.[dev]' | Out-Null
Write-Host "READY FOR TESTING"
