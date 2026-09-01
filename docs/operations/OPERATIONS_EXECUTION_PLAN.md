# Operations / Control Plane Execution Plan

## Current baseline

Existing repository automation already has a core CI gate for Ruff, MyPy, and Pytest on pushes and pull requests to `main`. The repository also has a system test script that runs unit tests, contract tests, integration tests, and a Docker build. See `.github/workflows/test.yml` and `scripts/test-system.sh`.

Operations should extend these controls rather than create a second competing test path.

## Phase 1 — Repository governance
- machine-readable Operations manifest
- agent ownership rules
- protected branch/review policy where available
- no force-push/rewrite policy
- migration immutability rule

## Phase 2 — CI quality gates
Current:
- Ruff
- MyPy
- Pytest

Required progression:
- contract/schema validation
- integration tests
- migration validation
- dependency/security checks
- secret scanning
- container build

A quality gate must block promotion when its required check fails.

## Phase 3 — Build and release
- produce immutable versioned artifacts
- record commit SHA/version in artifact metadata
- build Docker image reproducibly
- publish only from trusted release paths
- separate staging and production configuration

## Phase 4 — Runtime controls
- startup configuration validation
- liveness/readiness
- graceful shutdown
- restart recovery
- operational logs
- service identity
- correlation IDs

## Phase 5 — Safety controls
- global outbound kill switch
- campaign pause/resume
- mailbox pause/resume
- production-send enable gate
- maintenance mode where required
- audit trail for administrative changes

## Phase 6 — Observability and alerting
- service health
- queue depth/backlog
- error rates
- provider failures
- database connectivity
- deployment health
- worker crashes/restarts
- safety-state changes

## Phase 7 — Recovery
- database backup verification
- restore test
- application rollback
- migration recovery
- configuration recovery
- incident runbooks

## Phase 8 — Production gate
All relevant unit, contract, integration, concurrency, security, migration, container, staging-smoke, observability, and recovery gates pass. Real outbound effects remain disabled until the separate production approval is explicitly recorded.

## Operating principle
Operations provides the machinery and gates. Domain systems own their domain policies. Do not move business logic into CI/CD or the control plane merely because it is easier to orchestrate there.
