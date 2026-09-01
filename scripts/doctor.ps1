$ErrorActionPreference = "Continue"
$fail = 0
python --version *> $null; if ($LASTEXITCODE -ne 0) { Write-Host "Python FAIL"; $fail=1 }
docker --version *> $null; if ($LASTEXITCODE -ne 0) { Write-Host "Docker FAIL"; $fail=1 }
docker info *> $null; if ($LASTEXITCODE -ne 0) { Write-Host "Docker daemon FAIL"; $fail=1 }
if (-not (Test-Path .env.test)) { Write-Host ".env.test FAIL"; $fail=1 }
if (-not (Test-Path .venv/Scripts/python.exe)) { Write-Host "virtual environment FAIL"; $fail=1 }
if (Test-Path .env.test) {
  if (Select-String -Path .env.test -Pattern '^SL_REAL_EMAIL_ENABLED=(true|1|yes)$' -Quiet) { Write-Host "real email safety FAIL"; $fail=1 } else { Write-Host "real email safety PASS" }
}
if ($fail -eq 0) { Write-Host "DOCTOR RESULT: PASS" } else { Write-Host "DOCTOR RESULT: FAIL"; exit 1 }
