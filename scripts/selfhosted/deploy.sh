#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-compose.selfhosted.yml}"
ENV_FILE="${ENV_FILE:-.env}"
RELEASE_TAG="${RELEASE_TAG:-}"
STACK_NAME="${STACK_NAME:-sentinellayer}"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "ERROR: missing ${COMPOSE_FILE}" >&2
  exit 1
fi
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: missing ${ENV_FILE}; production configuration must be supplied outside Git" >&2
  exit 1
fi

if [[ "${SL_REAL_EMAIL_ENABLED:-false}" == "true" ]]; then
  echo "ERROR: export/validate production configuration explicitly before enabling real email" >&2
  exit 1
fi

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" config --quiet

if [[ -n "${RELEASE_TAG}" ]]; then
  export RELEASE_TAG
fi

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps

echo "Deployment started. Verify health/readiness before enabling outbound execution."
