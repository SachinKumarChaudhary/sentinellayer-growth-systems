# Operations Remaining Work

## Completed / implemented

- CI safety gate and environment safety checks
- dependency auditing
- lint/type/unit/contract gates
- Docker build and non-root validation
- runtime health/readiness
- graceful worker shutdown
- tag-based immutable release workflow
- self-hosted Compose baseline
- self-hosted edge/rate-limit policy
- static Nginx and Compose validation
- observability specification
- deployment adapter specification
- recovery drill specification
- production control-plane specification
- self-hosted deployment script
- self-hosted rollback script
- durable Operations control-state migration with RLS enabled and no permissive client policies
- metrics/alerting specification

## Remaining implementation

### 1. Observability implementation
Runtime/domain integrations must expose or collect the signals listed in `docs/operations/METRICS_ALERTS_SPEC.md`. Operations must provide collection/routing without creating a second business-state store.

### 2. Deployment verification
The deployment/rollback scripts are implemented, but actual execution requires the self-hosted laptop and valid external configuration. Production execution must remain disabled until the production gate passes.

### 3. Recovery drills
The procedures are documented but require an isolated staging environment for safe execution and evidence capture.

### 4. Production control plane
The durable state foundation is implemented. Authenticated administrative mutation and Mail-side enforcement are still required before `ENABLED` is usable.

### 5. Behavioral edge tests
Issue #9 remains dependent on the authoritative Tracking HTTP boundary.

## External dependencies

- Platform owns shared contract compatibility and cross-system tests.
- Campaign/Mail/Tracking own their domain semantics and thresholds.
- Real-provider staging and DNS/mailbox readiness remain Mail-owned.
- Tracking HTTP contract must be authoritative before behavioral edge testing.

## Production safety

Real outbound email remains disabled until the complete production-readiness gate passes and explicit human approval is recorded.
