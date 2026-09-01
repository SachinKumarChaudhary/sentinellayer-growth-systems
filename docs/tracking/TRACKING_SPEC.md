# Tracking & Behavioral Intelligence Specification

## Mission
Collect first-party, attributable behavioral observations after outreach and expose them as normalized, confidence-aware evidence to Intent, Conversation, and Analytics.

## Non-goals
- Do not decide commercial priority directly.
- Do not treat opens as authoritative human engagement.
- Do not send email.
- Do not bypass mail safety policies.
- Do not store raw recipient email addresses in public tracking URLs.

## Architecture

```text
Mail / Asset
   -> opaque token
   -> first-party endpoint
   -> validate + normalize request
   -> scanner/automation classification
   -> TrackingEvent
   -> deduplicate
   -> durable Supabase record
   -> behavioral timeline
   -> Intent / Conversation / Analytics
```

## Event trust model

| Observation | Default trust |
|---|---|
| Email open/pixel request | Low; may be automated |
| Link request | Low-to-medium until request is classified |
| Asset/page view | Medium when session behavior is coherent |
| Multiple coherent first-party events | Higher |
| Reply received | High lifecycle signal; owned by Conversation |
| Trial/signup/product event | High business signal when authenticated/verified |

Tracking records observations. Intent determines commercial meaning.

## Event taxonomy

### Mail-originated
`email_opened`, `link_clicked`, `asset_clicked`

### First-party content
`asset_viewed`, `asset_progressed`, `loom_started`, `loom_progressed`, `brief_viewed`, `brief_progressed`

### Web/product
`landing_viewed`, `docs_viewed`, `pricing_viewed`, `diagnostic_started`, `diagnostic_completed`, `trial_signup`, `sdk_installed`, `evaluate_called`

### Session
`session_started`, `session_resumed`, `session_ended`

Unknown event names may be ingested for forward compatibility only when they satisfy the generic contract; downstream scoring must ignore unknown events until explicitly registered.

## First-party links/assets

Trackable links and assets use cryptographically random opaque tokens. URLs must not contain email addresses, names, or sensitive identifiers.

The redirect/asset service must:
- accept HTTPS destinations only
- reject malformed destinations
- support revocation/expiration
- emit an event before redirect/render where safe
- avoid unnecessary redirect chains
- preserve campaign/send identity server-side

The custom Flipsnack alternative is an asset/content layer, not a mass tracking layer. Asset usage is selective and must not be injected into every cold email.

## Bot/scanner model

The system must distinguish:
- `automated`: strong scanner/bot evidence
- `human_candidate`: coherent browser/session evidence
- `unknown`: insufficient evidence

This classification is heuristic. It is never proof of human identity.

Signals may include user-agent markers, request method, path pattern, repeated requests, request timing, missing browser headers, known security-scanner signatures, and session coherence.

Do not permanently blacklist an IP from one request. Automated actors and shared networks can change behavior.

## Confidence

Every TrackingEvent has a confidence value `0.0–1.0` representing evidence quality, not buying probability.

Examples:
- scanner-like link request: `<= 0.2`
- unknown isolated browser request: `0.3–0.6`
- coherent multi-event browser session: `0.7–0.9`
- authenticated product event: `0.9+`

These are starting implementation values, not immutable scoring rules.

## Identity resolution

Resolution order:
1. authenticated first-party identifier when available
2. signed/opaque asset or link token mapping to person/send
3. session correlation
4. anonymous event

Never infer a person from IP address alone.

## Deduplication

Every inbound event should have a stable `source_event_id` when supplied by the producer. Otherwise the ingestion layer derives a deterministic `ingest_key` from stable request/event properties.

Duplicate ingestion must be idempotent.

## Privacy/security

- No raw IP persistence. If operationally required, store a one-way keyed hash managed outside the database schema.
- No email address in public tokens.
- Do not place sensitive research/personalization content in URLs.
- RLS remains enabled; public browser clients do not write directly to operational tracking tables.
- Ingestion should occur through a controlled first-party server endpoint using least-privilege service access.

## Intent integration

Tracking emits evidence; it does not mutate Intent directly.

```text
TrackingEvent
   -> Intent ingestion
   -> signal normalization
   -> freshness / confidence
   -> existing intent model
   -> priority decision
```

Existing buying-intent rules explicitly separate static FIT, decaying INTENT, and behavior overrides. Tracking therefore supplies behavior evidence rather than implementing the scoring model itself.

## Conversation integration

Tracking may provide context to Conversation, but replies remain authoritative conversation events.

A tracking event must never suppress or terminate an email sequence by itself unless a separate, explicitly approved campaign policy defines that behavior.

## Analytics integration

Every event preserves:
- account/person identity when known
- campaign/send identity when applicable
- correlation/causation IDs
- event timestamp
- schema version
- source system
- confidence

This allows strategy/message/CTA → event → meeting → opportunity → revenue attribution.

## Production acceptance criteria

- opaque tokens only
- no direct public DB writes
- duplicate events are idempotent
- scanner-like activity does not create false high-confidence engagement
- events preserve canonical IDs
- event records are queryable by account/person/campaign/send/session
- tracking cannot authorize a mail send
- synthetic end-to-end tracking tests pass
- RLS/security review passes
- retention and deletion policy is documented before production traffic
