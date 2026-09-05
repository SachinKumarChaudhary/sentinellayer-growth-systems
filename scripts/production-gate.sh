#!/usr/bin/env bash
set -euo pipefail

# Safe staging gate. Never enables real outbound email.
export SL_ENVIRONMENT="${SL_ENVIRONMENT:-development}"
export SL_REAL_EMAIL_ENABLED="${SL_REAL_EMAIL_ENABLED:-false}"

case "${SL_REAL_EMAIL_ENABLED,,}" in
  true|1|yes|on)
    echo "FAIL: real outbound email must remain disabled in the automated gate."
    exit 1
    ;;
esac

case "${SL_ENVIRONMENT,,}" in
  development|test|staging) ;;
  *)
    echo "FAIL: automated production gate cannot run with a production environment."
    exit 1
    ;;
esac

echo "Production gate harness: SAFE"
echo "Automated CI may validate deterministic software gates."
echo "Host/provider/database staging gates require explicit external evidence."
