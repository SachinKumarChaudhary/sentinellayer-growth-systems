#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-compose.selfhosted.yml}"
ENV_FILE="${ENV_FILE:-.env}"
ROLLBACK_TAG="${ROLLBACK_TAG:?ROLLBACK_TAG is required}"

[[ -f "${COMPOSE_FILE}" ]] || { echo "ERROR: missing ${COMPOSE_FILE}" >&2; exit 1; }
[[ -f "${ENV_FILE}" ]] || { echo "ERROR: missing ${ENV_FILE}" >&2; exit 1; }

export RELEASE_TAG="${ROLLBACK_TAG}"
export SL_REAL_EMAIL_ENABLED=false

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" config --quiet
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps

echo "Rollback deployed at RELEASE_TAG=${ROLLBACK_TAG} with real email disabled."
echo "Reconcile durable send state before resuming any outbound execution."
