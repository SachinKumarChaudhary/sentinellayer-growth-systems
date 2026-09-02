# Campaign Handoff

## Status
ACTIVE — Campaign / Messaging implementation.

## Completed
- Deterministic treatment resolver with stable SHA-256 experiment assignment.
- Campaign configuration validation and active-step integrity constraints.
- Enrollment service with fail-closed validation and idempotent treatment reuse.
- Sequence orchestrator that selects the next step and applies sequence delay without sending mail.

## Current files
- src/sentinellayer_growth_engine/resolver.py
- src/sentinellayer_growth_engine/enrollment.py
- src/sentinellayer_growth_engine/sequence.py
- tests/test_enrollment.py
- tests/test_sequence.py
- docs/01-campaigns/enrollment.md

## Database
Campaign owns campaign-domain migrations. Enrollment contract alignment and activation-hardening migrations are present on main. No new migration was added in this slice.

## Contracts
RenderedSendTreatment remains a shared Platform contract. This session consumes it at the Campaign → Mail boundary and does not modify the shared schema.

## Tests
Unit coverage added for enrollment and sequence progression. Full CI remains the completion gate; this handoff does not claim repository-wide CI is green.

## Dependencies
- Platform: shared RenderedSendTreatment contract and cross-system validation.
- Mail: delivery execution after Campaign produces a valid rendered treatment.
- Tracking/Conversation: downstream behavioral/reply signals used to terminate or alter campaign progression.

## Known limitation
Sequence progression currently provides pure orchestration. Atomic persistence of current_step_no/next_action_at and downstream termination signals must be implemented at the domain integration boundary before production activation.

## Next action
Implement the Campaign Treatment Renderer and validate its output against the shared RenderedSendTreatment schema without changing the shared contract.
