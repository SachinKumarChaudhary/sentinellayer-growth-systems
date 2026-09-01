#!/usr/bin/env bash
set -euo pipefail
[ -x .venv/bin/python ] || { echo "Run setup-test.sh first."; exit 1; }
. .venv/bin/activate
export SL_ENVIRONMENT=development
export SL_REAL_EMAIL_ENABLED=false
mkdir -p test-results
python -m ruff check .
python -m mypy src
python -m pytest -q
python -m pytest -q tests/contracts
python -m pytest -q tests/integration -m integration
docker build -t sentinellayer-growth-engine:test .
printf 'SentinelLayer Laptop Test Report\nResult: PASS\nReal email: DISABLED\nDocker image: sentinellayer-growth-engine:test\n' > test-results/test-report.txt
echo "RESULT: PASS"
