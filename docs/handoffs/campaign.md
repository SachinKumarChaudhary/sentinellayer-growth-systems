# Campaign Handoff

## Status
IN PROGRESS — Campaign / Messaging implementation.

## Completed
- Deterministic campaign treatment resolver with stable experiment assignment.
- Campaign configuration validation and activation hardening.
- Enrollment service with fail-closed validation and idempotent treatment reuse.
- Pure sequence orchestration.
- Campaign treatment rendering through the existing Campaign renderer and authoritative RenderedSendTreatment contract.
- Atomic campaign sequence-step claim/release/complete protocol backed by Supabase row locking and short-lived leases.
- Python repository adapter and unit tests for the claim protocol.

## Database
Supabase migration 20260902150000_campaign_step_claims.sql is applied successfully. The live database exposes claim_campaign_step(uuid,text,integer), release_campaign_step_claim(uuid,uuid), and complete_campaign_step_claim(uuid,uuid,integer,timestamptz), plus campaign enrollment step-claim lease columns.

The claim function locks the enrollment row, rejects non-active/paused/terminated states and future actions, prevents an unexpired duplicate claim, validates the sequence version/step references, and returns the frozen enrollment plus next-step routing data.

## Contracts
Campaign produces RenderedSendTreatment and must not send mail. Mail remains responsible for delivery. Shared schema ownership remains Platform.

## Tests
Unit tests were added for the claim repository. Live migration/function existence was verified directly in Supabase. Full repository CI remains the final completion gate.

## Dependencies
- Platform: shared RenderedSendTreatment contract and cross-system validation.
- Mail: delivery execution after Campaign produces a valid treatment.
- Tracking/Conversation: downstream signals must update campaign termination state through their owned boundaries.
- Operations: runtime scheduling/worker deployment.

## Known limitation
The claim protocol reserves a step but does not itself advance current_step_no. Completion must occur only after the downstream Mail boundary has safely accepted ownership of the send request. The exact cross-system acknowledgement is a Platform/Mail integration concern and must not be invented inside Campaign.

## Next action
Build the Campaign-to-Mail handoff adapter around the existing SendRequest contract, then add the cross-system integration test through the Platform-owned contract suite.