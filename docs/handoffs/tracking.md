# Tracking / Behavioral Intelligence Handoff

## Status
ACTIVE — foundation implemented; runtime exposure and production hardening remain.

## Current branch
`tracking/behavior-runtime-and-hardening`

No pull request has been opened yet. This branch is the isolated workspace for the next Tracking changes under the Multi-Agent Operating Protocol.

## Completed work

### Code
- `src/sentinellayer_growth_engine/tracking.py`
  - canonical tracking event construction
  - opaque token generation
  - HTTPS destination validation
  - keyed IP hashing
  - conservative traffic classification
  - evidence confidence
- `src/sentinellayer_growth_engine/tracking_repository.py`
  - durable tracking persistence
  - trackable-link resolution
  - asset-token resolution
  - session persistence
- `src/sentinellayer_growth_engine/tracking_service.py`
  - link-request ingestion
  - behavioral-event ingestion
  - identity/correlation propagation

### Database
Migration:
`supabase/migrations/20260901144317_tracking_behavior_foundation.sql`

Tracking structures include:
- `tracking.behavioral_events`
- `tracking.link_events`
- `tracking.trackable_links`
- `tracking.asset_tokens`
- `tracking.sessions`

The migration adds confidence/automation classification, correlation/idempotency fields, indexes, behavioral views, and RLS enablement for new tracking tables.

### Contract
Machine contract:
`schemas/tracking-event.schema.json`

Python validation is performed through the repository contract validator.

### Tests
`tests/test_tracking.py` covers:
- opaque token uniqueness
- HTTPS-only destinations
- keyed IP hashing
- scanner classification
- browser-signal classification
- conservative unknown classification
- confidence behavior
- TrackingEvent identity preservation
- closed event taxonomy at the Python boundary
- fail-closed invalid event/confidence handling

## Open coordination issues

- #1 — Operations: CI safety gate incorrectly rejects example environment files.
- #2 — Deliverability → Platform boundary readiness/dependencies.
- #3 — Tracking: implement first-party HTTP ingestion boundary.
- #4 — Tracking: define retention, privacy and deletion controls.
- #5 — Tracking: expand adversarial and evidence-quality tests.

Tracking must not bypass Issue #1 or weaken Operations-owned security gates.

## Dependencies

### Operations
Required for the approved runtime/deployment boundary for the first-party tracking endpoint. Tracking must integrate into the existing runtime rather than creating a competing deployment model.

### Platform
Required for:
- shared contract compatibility
- cross-system integration fixtures
- Campaign → Mail → Tracking lifecycle tests
- canonical event/correlation conventions where they are not already frozen

### Mail / Deliverability
Provides send/provider identity and canonical delivery outcomes. Tracking consumes those outcomes/events; it does not own delivery.

### Campaign
Produces the version-pinned treatment and eventually the tracked links/assets associated with a send.

### Conversation / Intent
Consume tracking evidence. Tracking does not assign commercial intent or sales outcomes.

## Contract boundary

```
Mail / Campaign
      ↓
send identity + tracking token
      ↓
First-party tracking endpoint
      ↓
TrackingService
      ↓
TrackingEvent
      ↓
Supabase
      ↓
Intent / Conversation / Analytics
```

Tracking provides evidence, not business conclusions.

## Known risks

1. TrackingService is not yet exposed through a production-approved HTTP runtime.
2. Scanner/bot classification is heuristic and must never be treated as proof of human identity.
3. Open/link events are noisy evidence and must not independently trigger strong intent.
4. Retention/deletion policy is not yet finalized.
5. Runtime abuse controls/rate limiting remain to be implemented.
6. Final Campaign → Mail → Tracking/Conversation E2E is pending.
7. CI currently has an Operations-owned safety-gate blocker.

## Next actions

1. Implement the first-party HTTP ingestion boundary on this branch after confirming the existing runtime contract.
2. Add endpoint-level tests for invalid, expired, revoked, duplicated and malformed requests.
3. Add retention/privacy/deletion policy and corresponding Supabase tests.
4. Expand adversarial traffic tests.
5. Run the complete Tracking unit + contract + integration suite.
6. Coordinate with Platform for the final cross-system event test.
7. Open a PR when the branch is reviewable.

## Handoff rule

The receiving agent must fetch the current branch/repository state before modifying files. Shared contracts or Operations-owned runtime files must not be silently changed. Use an Issue/PR for boundary changes.

## Definition of Done

Tracking is production-ready only when:
- endpoint is deployed through the approved runtime;
- events are validated and durably persisted;
- token expiry/revocation works;
- duplicate ingestion is controlled;
- scanner/automation evidence is conservative;
- privacy/retention controls are implemented;
- RLS/security requirements pass;
- unit, contract, integration and adversarial tests pass;
- Campaign/Mail/Tracking boundary tests pass;
- CI passes;
- documentation is updated.
