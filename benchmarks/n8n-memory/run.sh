#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$GITHUB_WORKSPACE"
OUT="$ROOT/benchmark-results"
WORKFLOW_JSON="$ROOT/benchmarks/n8n-memory/workflow.json"
CSV="$OUT/memory-metrics.csv"
mkdir -p "$OUT"
: > "$CSV"
printf 'timestamp_utc,version,phase,memory_bytes\n' > "$CSV"

python3 -m venv "$RUNNER_TEMP/n8n-bench-venv"
"$RUNNER_TEMP/n8n-bench-venv/bin/pip" install --quiet bcrypt
OWNER_HASH=$("$RUNNER_TEMP/n8n-bench-venv/bin/python" - <<'PY'
import bcrypt, secrets
password = secrets.token_urlsafe(32).encode()
print(bcrypt.hashpw(password, bcrypt.gensalt(rounds=4)).decode())
PY
)

sample_one() {
  local container="$1" version="$2" phase="$3"
  local raw value unit factor memory
  raw="$(docker stats --no-stream --format={{.MemUsage}} "$container" 2>/dev/null | head -n1 || true)"
  value="$(printf '%s' "$raw" | sed -E 's/^([0-9]+([.][0-9]+)?).*/\1/')"
  unit="$(printf '%s' "$raw" | sed -E 's/^[0-9]+([.][0-9]+)?[[:space:]]*([^[:space:]]+).*/\2/')"
  [[ "$value" =~ ^[0-9]+([.][0-9]+)?$ ]] || return 0
  case "$unit" in
    B) factor=1 ;;
    kB|KB) factor=1000 ;;
    KiB) factor=1024 ;;
    MB) factor=1000000 ;;
    MiB) factor=1048576 ;;
    GB) factor=1000000000 ;;
    GiB) factor=1073741824 ;;
    *) return 0 ;;
  esac
  memory="$(awk -v v="$value" -v f="$factor" 'BEGIN { printf "%.0f", v*f }')"
  printf '%s,%s,%s,%s\n' "$(date -u +%FT%TZ)" "$version" "$phase" "$memory" >> "$CSV"
}

sample_for_seconds() {
  local container="$1" version="$2" phase="$3" seconds="$4"
  local count=$((seconds * 2))
  for ((i=0; i<count; i++)); do
    sample_one "$container" "$version" "$phase"
    sleep 0.5
  done
}

sample_background() {
  local container="$1" version="$2" marker="$3"
  while [[ -f "$marker" ]]; do
    sample_one "$container" "$version" workload
    sleep 0.5
  done
}

wait_for_health() {
  local seconds="$1"
  for ((i=0; i<seconds; i++)); do
    if curl -fsS --max-time 2 http://127.0.0.1:5678/healthz/readiness >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

summarize_version() {
  local version="$1" state="$2" oom="$3" restart_count="$4" out_file="$5"
  python3 - "$CSV" "$version" "$state" "$oom" "$restart_count" "$out_file" <<'PY'
import csv, statistics, sys
csv_path, version, state, oom, restarts, output = sys.argv[1:]
rows = []
with open(csv_path, newline="") as f:
    for row in csv.DictReader(f):
        if row["version"] == version:
            rows.append((row["phase"], int(row["memory_bytes"])))
fmt = lambda n: f"{n / (1024**2):.1f} MiB" if n is not None else "n/a"
idle = [v for p, v in rows if p == "idle"]
load = [v for p, v in rows if p == "workload"]
post = [v for p, v in rows if p == "post-load"]
idle_median = statistics.median(idle) if idle else None
idle_peak = max(idle) if idle else None
load_peak = max(load) if load else None
overall_peak = max([v for _, v in rows], default=None)
with open(output, "a") as f:
    f.write(f"\n### {version}\n")
    f.write(f"- Result: **{state}**\n")
    f.write(f"- Node.js: see runtime file\n")
    f.write(f"- Idle median: {fmt(idle_median)}\n")
    f.write(f"- Idle sampled peak: {fmt(idle_peak)}\n")
    f.write(f"- Workload sampled peak: {fmt(load_peak)}\n")
    f.write(f"- Post-load median: {fmt(statistics.median(post) if post else None)}\n")
    f.write(f"- Overall sampled peak: {fmt(overall_peak)}\n")
    f.write(f"- OOMKilled: {oom}; restart count: {restarts}\n")
    f.write(f"- Sample count: {len(rows)}\n")
PY
}

run_version() {
  local version="$1" image="$2"
  local bootstrap="n8n-init-$version"
  local container="n8n-bench-$version"
  local pg="pg-bench-$version"
  local network="n8n-bench-net-$version"
  local dir="$OUT/$version"
  local status="PASS" failure=""
  mkdir -p "$dir"

  local env_args=(
    -e DB_TYPE=postgresdb
    -e DB_POSTGRESDB_HOST="$pg"
    -e DB_POSTGRESDB_PORT=5432
    -e DB_POSTGRESDB_DATABASE=n8nbench
    -e DB_POSTGRESDB_USER=bench
    -e DB_POSTGRESDB_PASSWORD=bench-only-not-real
    -e N8N_ENCRYPTION_KEY=disposable-n8n-benchmark-key-2026-only
    -e N8N_INSTANCE_OWNER_MANAGED_BY_ENV=true
    -e N8N_INSTANCE_OWNER_EMAIL=benchmark@example.com
    -e N8N_INSTANCE_OWNER_FIRST_NAME=Benchmark
    -e N8N_INSTANCE_OWNER_LAST_NAME=Only
    -e N8N_INSTANCE_OWNER_PASSWORD_HASH="$OWNER_HASH"
    -e N8N_RUNNERS_ENABLED=true
    -e N8N_RUNNERS_MODE=internal
    -e N8N_RUNNERS_MAX_CONCURRENCY=5
    -e N8N_RUNNERS_GRANT_TOKEN_TTL=120
    -e N8N_RUNNERS_TASK_TIMEOUT=300
    -e N8N_DIAGNOSTICS_ENABLED=false
    -e N8N_VERSION_NOTIFICATIONS_ENABLED=false
    -e N8N_LOG_LEVEL=warn
  )

  docker network create "$network" >/dev/null
  docker run -d --name "$pg" --network "$network" \
    --memory=512m --memory-swap=512m --cpus=0.5 \
    -e POSTGRES_USER=bench -e POSTGRES_PASSWORD=bench-only-not-real \
    -e POSTGRES_DB=n8nbench postgres:17-alpine >/dev/null

  local pg_ready=0
  for ((i=0; i<90; i++)); do
    if docker exec "$pg" pg_isready -U bench -d n8nbench >/dev/null 2>&1; then
      pg_ready=1
      break
    fi
    sleep 1
  done
  if [[ "$pg_ready" -ne 1 ]]; then
    status="FAIL"
    failure="PostgreSQL did not become ready"
  fi

  # Warm up the database and complete migrations using a generous temporary cap.
  if [[ -z "$failure" ]]; then
    docker run -d --name "$bootstrap" --network "$network" \
      -p 127.0.0.1:5678:5678 \
      --memory=1g --memory-swap=1g --cpus=1 --pids-limit=256 \
      "${env_args[@]}" "$image" >/dev/null

    if ! wait_for_health 300; then
      status="FAIL"
      failure="n8n did not become ready after database migration"
    else
      docker exec "$bootstrap" node --version > "$dir/node-version.txt" 2>&1 || true
      sleep 35
    fi
  fi

  if docker inspect "$bootstrap" >/dev/null 2>&1; then
    docker logs --tail 100 "$bootstrap" > "$dir/bootstrap.log" 2>&1 || true
    docker stop "$bootstrap" >/dev/null 2>&1 || true
    docker rm "$bootstrap" >/dev/null 2>&1 || true
  fi

  # Measure only the long-lived n8n process at the exact memory/CPU cap.
  if [[ -z "$failure" ]]; then
    docker run -d --name "$container" --network "$network" \
      -p 127.0.0.1:5678:5678 \
      --memory=512m --memory-swap=512m --cpus=0.1 --pids-limit=256 \
      "${env_args[@]}" "$image" >/dev/null

    if ! wait_for_health 300; then
      status="FAIL"
      failure="n8n did not become ready under 512 MiB / 0.1 CPU"
    else
      sleep 35
      docker exec "$container" node --version > "$dir/node-version.txt" 2>&1 || true
      sample_for_seconds "$container" "$version" idle 60
    fi
  fi

  if docker inspect "$container" >/dev/null 2>&1; then
    docker inspect -f 'OOMKilled={{.State.OOMKilled}} RestartCount={{.RestartCount}} ExitCode={{.State.ExitCode}}' "$container" > "$dir/container-state.txt" || true
    docker logs --tail 160 "$container" > "$dir/n8n.log" 2>&1 || true
    local oom restarts
    oom="$(docker inspect -f '{{.State.OOMKilled}}' "$container" 2>/dev/null || echo unknown)"
    restarts="$(docker inspect -f '{{.RestartCount}}' "$container" 2>/dev/null || echo unknown)"
    summarize_version "$version" "$status" "$oom" "$restarts" "$OUT/report.md"
  else
    printf '\n### %s\n- Result: **%s**\n- Failure: %s\n- No measured n8n container remained for inspection.\n' "$version" "$status" "$failure" >> "$OUT/report.md"
  fi

  [[ -z "$failure" ]] || printf '%s\n' "$failure" > "$dir/failure.txt"
  docker rm -f "$container" "$bootstrap" "$pg" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  echo "$version completed: $status ($failure)"
}

cat > "$OUT/report.md" <<'EOF'
# n8n image comparison — 512 MiB container cap

Both images run sequentially against PostgreSQL 17. A bootstrap server completes database migrations, then the measured instance starts with the same configuration and is capped at 512 MiB RAM and 0.1 CPU. The benchmark checks /healthz/readiness (database connected and migrated) rather than basic liveness. Internal task runners are enabled consistently, with concurrency 5 and a 120-second grant-token TTL. This first stage compares idle service footprint only; it does not claim a workflow-execution load test. The database runs separately. This is an isolated GitHub-hosted benchmark, not a reproduction of Render's full host or persisted service configuration.

EOF

run_version "2.30.7" "docker.io/n8nio/n8n@sha256:4da852b9488cf32bedc65ba1239216b50b0989f8187597e164b2901631954060"
run_version "2.45.7" "docker.io/n8nio/n8n@sha256:8e7fd6d66cef92bc0c7c049d456771d9003e9f69f9265c2238ab3f915ddbb080"

python3 - "$CSV" "$OUT/report.md" <<'PY'
import csv, statistics, sys
csv_path, report = sys.argv[1:]
with open(csv_path, newline="") as f:
    rows = list(csv.DictReader(f))
with open(report, "a") as f:
    f.write("\n## Raw results\n\n")
    f.write("| Version | Phase | Samples | Median | Peak |\n|---|---|---:|---:|---:|\n")
    for version in ("2.30.7", "2.45.7"):
        for phase in ("idle", "workload", "post-load"):
            values = [int(r["memory_bytes"]) for r in rows if r["version"] == version and r["phase"] == phase]
            if values:
                med = statistics.median(values) / (1024**2)
                peak = max(values) / (1024**2)
                f.write(f"| {version} | {phase} | {len(values)} | {med:.1f} MiB | {peak:.1f} MiB |\n")
PY

cat "$OUT/report.md"
