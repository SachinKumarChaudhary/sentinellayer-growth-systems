#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-compose.selfhosted.yml}"
ENV_FILE="${ENV_FILE:-.env}"
RELEASE_TAG="${ROLLBACK_TAG:-${RELEASE_TAG:-}}"

[[ -f "${COMPOSE_FILE}" ]] || { echo "ERROR: missing ${COMPOSE_FILE}" >&2; exit 1; }
[[ -f "${ENV_FILE}" ]] || { echo "ERROR: missing ${ENV_FILE}" >&2; exit 1; }
[[ -n "${RELEASE_TAG}" ]] || { echo "ERROR: RELEASE_TAG is required" >&2; exit 1; }

export SL_REAL_EMAIL_ENABLED=false
export RELEASE_TAG

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" config --quiet
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build

echo "Rollback deployed: RELEASE_TAG=${RELEASE_TAG}"
echo "Real outbound email remains disabled."
echo "Reconcile durable send state before re-enabling outbound execution."
