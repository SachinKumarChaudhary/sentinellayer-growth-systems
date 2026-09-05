# Operations Handoff

**Status:** ACTIVE / IN PROGRESS
**Owner:** operations
**Target:** self-hosted laptop production runtime

## Current implemented scope

- CI safety/environment gate and dependency auditing
- lint/type/unit/contract tests
- Docker/non-root verification
- runtime health/readiness
- graceful worker shutdown
- immutable release baseline
- self-hosted Compose and Nginx edge baseline
- deployment/rollback scripts
- durable Operations control-state migration with RLS
- fail-closed default control-state initialization
- metrics/alerting and recovery-drill specifications

## Cross-system status

- Platform canonical contracts are on main.
- Tracking runtime/first-party HTTP boundary is on main and has passed its integration CI.
- Campaign and Mail retain domain ownership.
- Operations consumes Tracking's authoritative HTTP boundary; it does not duplicate tracking semantics.

## Remaining production gates

1. Authenticated administrative control surface and audit mutation path.
2. Mail execution enforcement of Operations control state; state lookup failure must block real send.
3. Runtime telemetry/alert routing implementation.
4. Behavioral edge/load testing through the merged Tracking HTTP boundary.
5. Self-hosted staging deployment and recovery drills.
6. Final Campaign → Mail → Tracking → Conversation synthetic E2E.
7. Real provider/DNS/mailbox staging validation.

## Safety

Real outbound email remains disabled until all production gates pass and explicit human approval is recorded.

## Boundary rule

Operations owns runtime, deployment, observability, control mechanisms, and recovery. Platform owns shared contracts. Campaign, Mail, Tracking, and Conversation own their respective domain semantics.

No production control state transition may bypass domain eligibility, suppression, or provider safety policy.
