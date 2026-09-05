# Operations Handoff

**Status:** ACTIVE / IN PROGRESS
**Owner:** operations
**Protocol:** `docs/architecture/MULTI_AGENT_OPERATING_PROTOCOL.md`
**Target:** self-hosted laptop production runtime

## Implemented

- CI safety gate and environment checks
- dependency auditing
- lint/type/unit/contract gates
- Docker build and non-root validation
- runtime health/readiness
- graceful worker shutdown
- immutable release workflow baseline
- self-hosted runtime and edge policies
- static Nginx/Compose validation
- self-hosted deployment/rollback scripts
- durable Operations control-state migration with RLS enabled and no permissive client policies
- metrics/alerting specification
- execution-status and remaining-work documentation

## Remaining

1. Implement authenticated administrative control endpoint and audit flow.
2. Integrate Mail execution with durable production control state; fail closed on control-state failure.
3. Implement runtime telemetry collection/alert routing.
4. Execute self-hosted staging deployment, rollback, reboot, network-interruption, and restore drills.
5. Execute behavioral edge/load tests after Tracking HTTP contract is authoritative.
6. Verify CI evidence and close Operations-owned issues only after acceptance criteria are evidenced.

## Ownership

- Operations owns runtime, deployment, observability, control mechanisms, and recovery.
- Platform owns shared schemas/contracts and cross-system tests.
- Mail/Campaign/Tracking retain domain policy and implementation ownership.

## Safety

Real outbound mail remains disabled until all production gates pass and explicit human approval is recorded.

## Known cross-system blockers

- Platform issue #10: RenderedSendTreatment schema/fixture reconciliation.
- Tracking PR #6: first-party HTTP boundary remains unmerged/draft.
- Tracking issue #8: semantic replay/idempotency decision.
- Operations issue #9: behavioral self-hosted edge/load tests.

## Next action

Complete the Operations control API/enforcement integration only through explicit producer/consumer contracts. Do not modify shared domain schemas from Operations.
