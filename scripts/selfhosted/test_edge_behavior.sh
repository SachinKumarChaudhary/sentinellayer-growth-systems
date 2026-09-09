#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/ops/nginx/compose.edge-test.yml")
BASE="http://127.0.0.1:18080"
TOKEN="TestOpaqueToken_1234567890"
BODY_MARKER="SHOULD_NEVER_APPEAR_IN_EDGE_LOGS_9f3c"

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    "${COMPOSE[@]}" ps || true
    timeout 5s "${COMPOSE[@]}" logs --no-color edge upstream || true
  fi
  "${COMPOSE[@]}" kill >/dev/null 2>&1 || true
  timeout 10s "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT

timeout 60s "${COMPOSE[@]}" up -d
"${COMPOSE[@]}" ps

for _ in $(seq 1 30); do
  if curl -fsS --max-time 1 -o /dev/null "$BASE/healthz"; then break; fi
  sleep 1
done
curl -fsS --max-time 2 -o /dev/null "$BASE/healthz"

printf '%s\n' "[1/8] health/readiness"
test "$(curl -fsS --max-time 2 -o /dev/null -w '%{http_code}' "$BASE/healthz")" = 200
test "$(curl -fsS --max-time 2 -o /dev/null -w '%{http_code}' "$BASE/readyz")" = 200

printf '%s\n' "[2/8] normal tracking request remains available"
test "$(curl -fsS --max-time 2 -o /dev/null -w '%{http_code}' "$BASE/t/$TOKEN")" = 200
test "$(curl -fsS --max-time 2 -o /dev/null -w '%{http_code}' -X POST --data "$BODY_MARKER" "$BASE/t/$TOKEN")" = 200

printf '%s\n' "[3/8] burst traffic is rate limited"
timeout 20s bash -c 'seq 1 50 | xargs -P50 -I{} curl -sS --max-time 2 -o /dev/null -w "%{http_code}\n" "$0/t/rate-{}-123456789012345" > /tmp/rate-statuses' "$BASE"
awk '$1 == 503 { rejected++ } END { exit(rejected > 0 ? 0 : 1) }' /tmp/rate-statuses

printf '%s\n' "[4/8] concurrent connections are capped"
timeout 20s bash -c 'seq 1 64 | xargs -P64 -I{} curl -sS --max-time 5 -o /dev/null -w "%{http_code}\n" "$0/c/slow-{}-123456789012345" > /tmp/conn-statuses' "$BASE" || true
awk '$1 == 503 { rejected++ } END { exit(rejected > 0 ? 0 : 1) }' /tmp/conn-statuses

printf '%s\n' "[5/8] oversized requests are rejected at the edge"
test "$(head -c 40960 /dev/zero | curl -sS --max-time 2 -o /dev/null -w '%{http_code}' -X POST --data-binary @- "$BASE/t/$TOKEN")" = 413

printf '%s\n' "[6/8] upstream timeout is surfaced safely"
test "$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' "$BASE/t/timeout-123456789012345")" = 504

printf '%s\n' "[7/8] restart/recovery restores service"
"${COMPOSE[@]}" restart upstream >/dev/null
for _ in $(seq 1 20); do
  if test "$(curl -sS --max-time 2 -o /dev/null -w '%{http_code}' "$BASE/t/recovery-123456789012345")" = 200; then
    break
  fi
  sleep 1
done
test "$(curl -sS --max-time 2 -o /dev/null -w '%{http_code}' "$BASE/t/recovery-123456789012345")" = 200

printf '%s\n' "[8/8] rejected traffic is observable without sensitive request data"
curl -sS --max-time 2 -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -X POST -d "$BODY_MARKER" "$BASE/t/log-safety" | grep -Eq '^(200|503)$'
LOGS="$(timeout 5s "${COMPOSE[@]}" logs --no-color edge)"
printf '%s\n' "$LOGS" | grep -q 'status=503'
if printf '%s\n' "$LOGS" | grep -Fq "$TOKEN"; then
  echo "FAIL: opaque tracking token leaked into edge logs" >&2
  exit 1
fi
if printf '%s\n' "$LOGS" | grep -Fq "$BODY_MARKER"; then
  echo "FAIL: request body leaked into edge logs" >&2
  exit 1
fi
if printf '%s\n' "$LOGS" | grep -Eiq '(password|authorization:|secret|api[_-]?key|bearer)'; then
  echo "FAIL: credential-like material leaked into edge logs" >&2
  exit 1
fi

echo "Edge behavioral tests: PASS"
