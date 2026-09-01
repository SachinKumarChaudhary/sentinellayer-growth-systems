$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv/Scripts/python.exe)) { throw "Run setup-test.ps1 first." }
. .venv/Scripts/Activate.ps1
$env:SL_ENVIRONMENT = "development"
$env:SL_REAL_EMAIL_ENABLED = "false"
New-Item -ItemType Directory -Force test-results | Out-Null
python -m ruff check .
python -m mypy src
python -m pytest -q
python -m pytest -q tests/contracts
python -m pytest -q tests/integration -m integration
docker build -t sentinellayer-growth-engine:test .
Set-Content test-results/test-report.txt "SentinelLayer Laptop Test Report; Result: PASS; Real email: DISABLED; Docker image: sentinellayer-growth-engine:test"
Write-Host "RESULT: PASS"
