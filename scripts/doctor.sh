#!/usr/bin/env bash
set -u
fail=0
echo "SentinelLayer Doctor"
python3 --version >/dev/null 2>&1 || { echo "Python FAIL"; fail=1; }
docker --version >/dev/null 2>&1 || { echo "Docker FAIL"; fail=1; }
docker info >/dev/null 2>&1 || { echo "Docker daemon FAIL"; fail=1; }
[ -f .env.test ] || { echo ".env.test FAIL"; fail=1; }
[ -x .venv/bin/python ] || { echo "virtual environment FAIL"; fail=1; }
if [ -f .env.test ] && grep -Eiq '^SL_REAL_EMAIL_ENABLED=(true|1|yes)$' .env.test; then echo "real email safety FAIL"; fail=1; else echo "real email safety PASS"; fi
if [ "$fail" -eq 0 ]; then echo "DOCTOR RESULT: PASS"; else echo "DOCTOR RESULT: FAIL"; exit 1; fi
