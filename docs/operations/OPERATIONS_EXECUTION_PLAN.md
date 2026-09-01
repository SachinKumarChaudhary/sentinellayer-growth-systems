# Operations / Control Plane Execution Plan

## Current baseline

Existing repository automation has a core CI gate for Ruff, MyPy, Pytest, contract tests, dependency auditing, Docker build validation, and CI safety controls. A system test script also exists for the broader unit/contract/integration/Docker path.

Operations extends these controls rather than creating competing test paths.

## Phase 1 — Repository governance
- machine-readable Operations manifest
- agent ownership rules
- protected branch/review policy where available
- no force-push/rewrite policy
- migration immutability rule

## Phase 2 — CI quality gates
Implemented:
- Ruff
- MyPy
- Pytest
- explicit contract-test gate
- CI safety gate enforcing non-production environment and real-email disabled
- dependency audit
- Docker build gate
- non-root container assertion
- least-privilege workflow permissions
- CI concurrency cancellation
- CI metadata artifact

## Phase 3 — Build and release
Implemented:
- tag-based release workflow
- immutable version/commit labels on release image
- release manifest
- exported release artifact
- release quality and safety gates

Not implemented yet:
- external container registry publication
- automatic production deployment

These remain deployment-target decisions and require the selected production platform.

## Phase 4 — Runtime controls
Implemented:
- container healthcheck for process liveness and PostgreSQL readiness
- startup configuration validation in the application
- graceful shutdown in the mail worker

Remaining:
- runtime-specific deployment adapter
- centralized operational logs/metrics
- deployment version endpoint where required by the selected runtime

## Phase 5 — Safety controls
Defined by contract:
- global outbound kill switch
- campaign pause/resume
- mailbox pause/resume
- production-send enable gate
- maintenance mode
- administrative audit trail

Implementation of domain-specific pause/eligibility semantics remains with the owning domain systems. Operations owns the control plane and emergency override mechanism.

## Phase 6 — Observability and alerting
Defined:
- service health
- queue depth/backlog
- error rates
- provider failures
- database connectivity
- deployment health
- worker crashes/restarts
- safety-state changes

Remaining:
- select metrics/logging backend
- configure alert thresholds with domain owners
- wire runtime alerts

## Phase 7 — Recovery
Defined:
- database backup verification
- isolated restore test
- application rollback
- migration recovery
- configuration recovery
- incident runbooks

Remaining:
- execute the first real restore/rollback drills after staging infrastructure exists

## Phase 8 — Production gate
All relevant unit, contract, integration, concurrency, security, migration, container, staging-smoke, observability, and recovery gates must pass. Real outbound effects remain disabled until the separate production approval is explicitly recorded.

## Operating principle
Operations provides the machinery and gates. Domain systems own domain policies. Do not move business logic into CI/CD or the control plane merely because it is easier to orchestrate there.
