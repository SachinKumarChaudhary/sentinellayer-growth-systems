#!/usr/bin/env bash
set -euo pipefail

# CI safety gate: this script must never enable real outbound side effects.
export SL_ENVIRONMENT="${SL_ENVIRONMENT:-development}"
export SL_REAL_EMAIL_ENABLED="${SL_REAL_EMAIL_ENABLED:-false}"

case "${SL_REAL_EMAIL_ENABLED,,}" in
  true|1|yes|on)
    echo "FAIL: SL_REAL_EMAIL_ENABLED is enabled in CI."
    exit 1
    ;;
esac

case "${SL_ENVIRONMENT,,}" in
  development|test|staging) ;;
  *)
    echo "FAIL: CI must run in a non-production environment."
    exit 1
    ;;
esac

if [[ -f .env.test ]] && grep -Eiq '^SL_REAL_EMAIL_ENABLED=(true|1|yes|on)[[:space:]]*$' .env.test; then
  echo "FAIL: .env.test enables real email."
  exit 1
fi

if git ls-files -z | grep -Eizq '(^|/)(\.env|\.env\..*|.*\.pem|.*\.key)$'; then
  echo "FAIL: tracked environment/credential file detected."
  git ls-files | grep -Ei '(^|/)(\.env|\.env\..*|.*\.pem|.*\.key)$' || true
  exit 1
fi

python -m pip check

echo "CI safety gate: PASS"
echo "Environment: ${SL_ENVIRONMENT}"
echo "Real email: disabled"
