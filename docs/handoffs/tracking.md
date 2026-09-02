# Tracking / Behavioral Intelligence Handoff

## Status
ACTIVE — foundation implemented; first-party HTTP link-tracking boundary implemented on this isolated branch. Production hardening and Operations runtime integration remain.

## Branch
`tracking/behavior-runtime-and-hardening`

## Completed
- Tracking event construction and schema validation.
- Conservative traffic classification and evidence confidence.
- Opaque tracking-token generation.
- HTTPS-only destination validation.
- Keyed IP hashing.
- Durable PostgreSQL tracking repository.
- Idempotent behavioral/link event persistence.
- Trackable-link and asset-token persistence/resolution.
- Session persistence.
- Supabase tracking foundation and RLS.
- Unit tests for tracking behavior.
- First-party HTTP link boundary in `src/sentinellayer_growth_engine/tracking_http.py`.
- Endpoint liveness/readiness responses.
- Fail-closed token validation.
- Server-side identity resolution; client cannot supply account/person/campaign/send identity for link redirects.
- Security response headers and bounded request metadata.
- No database/runtime error details returned to clients.

## Current HTTP boundary
```
GET /t/<opaque-token>
        ↓
server-side token resolution
        ↓
TrackingService.ingest_link_request()
        ↓
TrackingEvent + durable link event
        ↓
302 validated HTTPS destination
```

`/a/<token>` is intentionally not exposed yet because asset view/click/byte-serving semantics must be fixed by the shared contract before implementation.

## Exact files on this branch
- `src/sentinellayer_growth_engine/tracking.py`
- `src/sentinellayer_growth_engine/tracking_repository.py`
- `src/sentinellayer_growth_engine/tracking_service.py`
- `src/sentinellayer_growth_engine/tracking_http.py`
- `tests/test_tracking.py`
- `tests/test_tracking_http.py`
- `supabase/migrations/20260901144317_tracking_behavior_foundation.sql`
- `schemas/tracking-event.schema.json`

## Dependencies / ownership
- Operations owns deployment/runtime integration, CI/CD, production networking, rate limiting infrastructure, and operational controls.
- Platform owns shared contract compatibility and cross-system integration tests.
- Mail provides send/provider identity; Tracking does not send mail.
- Campaign provides campaign/treatment context; Tracking does not implement campaign strategy.
- Intent/Conversation consume behavioral evidence; Tracking does not assign commercial intent.

## Open issues
- #1 Operations CI safety-gate blocker.
- #3 first-party HTTP tracking boundary.
- #4 retention/privacy/deletion controls.
- #5 adversarial/evidence-quality tests.
- #8 semantic replay/idempotency contract for GET link events — contract proposed; public-header trust issue resolved; Platform compatibility review pending.

Issue #3 is now implemented at the code boundary but remains open until runtime integration and endpoint tests pass through CI.

## Known risks
1. The standard-library HTTP server is an application boundary, not a deployment decision. Operations must integrate it into the approved production runtime.
2. Rate limiting/abuse controls are not yet implemented.
3. Scanner/bot classification is heuristic and never proves human identity.
4. Open/link behavior remains weak evidence.
5. Retention/deletion policy is not finalized.
6. Asset-token semantics are intentionally gated.
7. Full Campaign → Mail → Tracking → Conversation E2E is pending.
8. CI has an Operations-owned safety-gate blocker.

## Next actions
1. Run CI against this branch and fix only Tracking-owned failures.
2. Add endpoint tests using an isolated fake repository/service boundary; do not require a production database for unit tests.
3. Add retention/privacy/deletion controls and real-Supabase tests.
4. Add adversarial request/replay/scanner tests.
5. Coordinate with Operations for deployment/runtime integration.
6. Coordinate with Platform for the final TrackingEvent and cross-system integration fixtures.
7. Close #3 only after runtime integration and CI are green.
8. Open a review PR when the branch is ready.

## Definition of Done
Tracking is production-ready only when endpoint/runtime integration, security/RLS, retention/deletion, token expiry/revocation, idempotency, conservative evidence classification, unit/contract/integration/adversarial tests, cross-system tests, CI, and documentation all pass without violating subsystem ownership.

## Multi-agent rule
Receiving agents must fetch current repository state before editing. Shared contracts and Operations-owned runtime files must not be changed silently. Cross-system changes use Issues/PRs and Platform compatibility review.
