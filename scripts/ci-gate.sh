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

tracked_bad="$(git ls-files | grep -Ei '(^|/)(\.env|\.env\.[^/]+|.*\.pem|.*\.key)

python -m pip check

echo "CI safety gate: PASS"
echo "Environment: ${SL_ENVIRONMENT}"
echo "Real email: disabled"
 | grep -Eiv '(^|/)\.env\.example$|(^|/)\.env\.test\.example

python -m pip check

echo "CI safety gate: PASS"
echo "Environment: ${SL_ENVIRONMENT}"
echo "Real email: disabled"
 || true)"
if [[ -n "${tracked_bad}" ]]; then
  echo "FAIL: tracked environment/credential file detected."
  printf '%s\n' "${tracked_bad}"
  exit 1
fi

for template in .env.example .env.test.example; do
  if [[ -f "${template}" ]] && grep -Eiq '^[[:space:]]*(SL_REAL_EMAIL_ENABLED|SMTP_HOST|SMTP_USERNAME|SMTP_PASSWORD|SL_DATABASE_URL)[[:space:]]*=' "${template}"; then
    echo "FAIL: example environment template contains a live credential/capability setting: ${template}"
    exit 1
  fi
done

python -m pip check

echo "CI safety gate: PASS"
echo "Environment: ${SL_ENVIRONMENT}"
echo "Real email: disabled"
