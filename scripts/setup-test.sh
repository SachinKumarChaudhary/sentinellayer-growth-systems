#!/usr/bin/env bash
set -euo pipefail
echo "SentinelLayer Laptop Test Setup"
command -v python3 >/dev/null || { echo "FAIL: Python 3.11+ required"; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3,11)'
command -v docker >/dev/null || { echo "FAIL: Docker required"; exit 1; }
docker info >/dev/null 2>&1 || { echo "FAIL: Docker daemon is not running"; exit 1; }
if [ ! -f .env.test ]; then cp .env.test.example .env.test; fi
if grep -Eiq '^SL_REAL_EMAIL_ENABLED=(true|1|yes)$' .env.test; then echo "FAIL: real email enabled"; exit 1; fi
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -e '.[dev]' >/dev/null
echo "READY FOR TESTING"
