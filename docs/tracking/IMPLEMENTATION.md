# Tracking & Behavioral Intelligence — Implementation Plan

## Implemented

### Database
- `tracking.behavioral_events` extended with account/correlation IDs, confidence, automation classification, source-event identity, and ingest idempotency key.
- `tracking.link_events` extended with the same operational metadata.
- `tracking.trackable_links` provides opaque first-party redirect tokens.
- `tracking.asset_tokens` provides opaque first-party asset tokens for Loom/brief/landing assets.
- `tracking.sessions` stores minimal session correlation state.
- RLS enabled on all tracking operational tables.
- Timeline/link-engagement views added for downstream consumers.

### Python
`src/sentinellayer_growth_engine/tracking.py` provides:
- canonical tracking event taxonomy
- opaque URL-safe token generation
- HTTPS destination validation
- keyed IP hashing helper (raw IP never persisted)
- conservative scanner/automation classification
- confidence defaults
- TrackingEvent construction + shared-contract validation

### Tests
`tests/test_tracking.py` covers token uniqueness, URL safety, IP hashing, automation classification, confidence, event construction, and fail-closed validation.

## Runtime architecture

```text
Email / Loom / First-party asset
              ↓
       opaque public token
              ↓
       controlled HTTPS endpoint
              ↓
    validate + classify request
              ↓
          TrackingEvent
              ↓
        idempotent ingest
              ↓
          Supabase
              ↓
   ┌──────────┼───────────┐
   ↓          ↓           ↓
 Intent   Conversation  Analytics
```

The browser/client must not write directly to the tracking tables. The first-party ingestion service is the trust boundary.

## Trust model

A tracking event is an observation, not a business conclusion.

- Email opens: weak evidence.
- Isolated link requests: uncertain until classified.
- Coherent first-party sessions: stronger evidence.
- Authenticated product events: strongest behavioral evidence.
- Replies and commercial outcomes remain owned by Conversation/Sales.

Automated traffic is explicitly classified and should not be promoted to strong intent based on a scanner hit.

## Integration dependencies

### Mail → Tracking
Mail produces `ProviderOutcome` and durable send identity. Tracking may correlate `send_id`, campaign, person, and provider-related events.

### Campaign → Tracking
Campaign supplies asset/link intent through `RenderedSendTreatment`; Tracking does not modify campaign strategy.

### Tracking → Intent
Tracking provides `TrackingEvent` evidence. Intent remains responsible for scoring, decay, negative flags, and P1/P2/P3/P4 routing.

### Tracking → Conversation
Tracking provides context. Conversation owns reply meaning and conversation state.

### Tracking → Analytics
Tracking preserves attribution identifiers and timestamps so analytics can attribute events to campaign/strategy/message/CTA versions.

## Production hardening still required

1. Implement the first-party HTTP ingestion service.
2. Implement secure opaque-token lookup and redirect/render flow.
3. Add request rate limiting and abuse controls.
4. Add scanner/header/timing heuristics calibrated against synthetic fixtures.
5. Add event deduplication integration tests against Supabase.
6. Add session lifecycle persistence/update logic.
7. Add retention/deletion policy implementation.
8. Add contract test proving Mail → Tracking identity preservation.
9. Add contract test proving Tracking → Intent evidence delivery.
10. Add end-to-end synthetic lifecycle coverage.

## Explicit non-goals

- No open-rate optimization as a primary KPI.
- No direct P1 promotion from a single tracking event.
- No raw email address in public URLs.
- No raw IP storage.
- No tracking pixel/link injection into every cold email by default.
- No outbound-send authorization from Tracking.
