# Deliverability Handoff

## Status
ACTIVE — mail execution implementation is substantially complete; remaining work is production hardening and cross-system verification.

## Completed
- Durable mail execution state and queue claiming.
- Worker lease/reclaim behavior.
- Idempotent send handling.
- Retry classification.
- Ambiguous-delivery handling and reconciliation state.
- SMTP/provider abstraction and normalized provider outcomes.
- Eligibility/suppression safety gates.
- Deterministic send identifiers.
- Unit and Supabase concurrency coverage.
- Docker/CI support for the mail runtime.

## Current ownership boundary
Deliverability / Mail owns:
- SMTP/provider abstraction
- mailbox/provider configuration
- durable send state
- queue claiming and worker leases/reclaim
- idempotency
- retry classification
- ambiguous-delivery handling
- mail execution
- send migrations/tests
- production mail runtime

Platform owns the shared schemas, contract validation, cross-system integration tests, shared identifiers/event envelopes, and integration harnesses. Campaign owns Resolver/rendering/enrollment. Deliverability must not implement Campaign strategy or silently change shared contracts.

## Current priority
Complete Deliverability production gates while Platform completes the Campaign → Mail boundary and cross-system verification.

## Remaining Deliverability gates
- Controlled real-provider staging smoke test.
- Production DNS/mailbox readiness verification.
- Operational metrics and alerts.
- Explicit mailbox/domain rate limits.
- Inbound adapter if required by the product contract.
- Provider-specific bounce/complaint ingestion where supported.
- Reconciliation evidence/operator tooling.
- Deployment/runtime smoke test.
- Production rollback procedure.
- Final Campaign → Send → Tracking/Conversation E2E.

## Cross-system dependency
The current repository priority is:

Shared schemas + validation
→ Campaign Resolver
→ RenderedSendTreatment
→ Mail-engine boundary adapter
→ Campaign → Mail integration tests
→ Supabase-backed end-to-end tests
→ Full lifecycle verification

Deliverability is ready to consume a validated send contract. The next cross-system dependency is Platform-owned boundary/integration verification; Deliverability should only change its implementation when a failing boundary test is attributable to Mail-owned behavior.

## CI / blocker note
The current CI safety-gate issue is already tracked as GitHub Issue #1: "Fix CI safety gate false positive on example environment files". That issue assigns CI/CD ownership to Operations / Control Plane and explicitly says Platform/Tracking should not bypass or weaken the gate. Deliverability is not claiming ownership of that fix.

## Tests / results
- Mail unit/concurrency coverage is present in the repository.
- GitHub Actions is operational.
- Do not treat a Platform/Operations CI failure as a Deliverability defect without tracing the failing job to Mail-owned code.

## Dependencies
- Platform: cross-system contract fixtures, boundary validation, synthetic lifecycle integration tests.
- Operations: CI/CD safety-gate fix, deployment/runtime configuration and operational controls.
- Campaign: producer-side RenderedSendTreatment behavior.
- Tracking/Conversation: final lifecycle consumers.

## Blockers
No open Deliverability-specific GitHub issue was found in the current repository search. Production validation remains pending because it requires controlled provider/staging configuration and cross-system prerequisites.

## Known risks
- Real-provider behavior has not been substituted for unit tests; controlled staging verification remains required.
- Rate limits, bounce/complaint handling, operational monitoring, and rollback need production-level validation.
- Cross-system E2E must prove that the validated Campaign treatment reaches Mail execution without duplicated strategy logic.

## Next action
Deliverability: prepare/validate the remaining production gates without changing Platform-owned contracts.

Receiving subsystem: Platform / Cross-System for the boundary and integration dependencies; Operations / Control Plane for the existing CI safety-gate issue.

## Coordination
Technical coordination is recorded here and through GitHub issues/PRs according to docs/architecture/MULTI_AGENT_OPERATING_PROTOCOL.md.