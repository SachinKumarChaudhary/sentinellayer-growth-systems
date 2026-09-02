# Platform Canonical Contracts

**Owner:** Platform  
**Status:** Active baseline  
**Purpose:** Define machine-enforceable cross-system contracts without owning subsystem business logic.

## Contract hierarchy

Master System Contracts -> Canonical schemas -> Subsystem implementations -> Contract tests / CI

Platform owns shared contract semantics. Subsystems own their domain logic and implementation.

## Canonical event envelope

Machine-readable baseline: schemas/event-envelope.schema.json.

Required: event_id, event_type, occurred_at, source_system, environment, correlation_id, schema_version, payload.

Optional attribution: account_id, person_id, lead_id, campaign_id, send_id, causation_id, confidence.

Rules:
1. Canonical identifiers are preserved across boundaries.
2. Consumers do not silently replace producer-owned identity.
3. correlation_id connects one distributed business operation.
4. causation_id identifies the immediate triggering event when applicable.
5. schema_version is mandatory; breaking changes require a new version.
6. confidence is bounded to 0..1 and is used only where interpretation/uncertainty exists.
7. Secrets and unnecessary personal data are excluded from event payloads.

## RenderedSendTreatment

Machine-readable baseline: schemas/rendered-send-treatment.schema.json.

Campaign owns treatment selection/rendering. Mail owns execution and deterministic safety policy. Campaign must not write Mail queue state directly.

The treatment preserves campaign enrollment and person/account identity, sequence step, strategy/offer/message/CTA/sequence versions, experiment assignment, recipient/rendered content, selected asset/personalization data, and render timestamp.

## Tracking replay semantics

Tracking public HTTP is intentionally non-idempotent for ordinary GET observations. A public client-supplied X-Idempotency-Key is not trusted.

Future semantic retries require an authenticated/internal producer boundary. Until then, repeated GETs for the same public token remain separate observations.

## Cross-system rules

### Campaign -> Mail
A valid RenderedSendTreatment is the input contract. Mail validates it and applies deterministic eligibility/safety gates.

### Mail -> Tracking
Mail/provider identity and send context may be used for attribution. Tracking records observations; it does not send mail or assign commercial intent.

### Tracking -> Intent/Analytics
Tracking produces evidence. Downstream systems determine commercial significance.

### Conversation -> Sales
Conversation produces normalized conversation state and handoff context. Sales owns opportunity/revenue state.

### All systems -> Analytics
Analytics consumes durable events and outcomes. Analytics does not become the source of truth for operational state.

## Version compatibility

- Additive backward-compatible changes are permitted within a version only when consumers tolerate them.
- Removing/renaming required fields or changing field meaning is breaking.
- Breaking changes require a new schema version.
- Producers must not emit unsupported versions.
- Consumers must explicitly reject unsupported breaking versions.
- Historical records retain the version used at execution time.

## Platform validation gate

Every shared contract must have a machine-readable schema, explicit producer/consumer ownership, valid fixture, invalid fixture, unsupported-version fixture, identity/correlation preservation test, idempotency test where applicable, and CI execution.

Platform validates boundaries; it does not import private implementation details of another subsystem as a substitute for the public contract.

## Current priority

1. Validate Campaign -> Mail treatment compatibility.
2. Validate Mail/provider outcome -> Tracking attribution.
3. Validate Tracking -> downstream evidence contract.
4. Validate Conversation -> future Sales handoff fixture.
5. Build the synthetic end-to-end contract test.
6. Make CI enforce the contract gate.

Intelligence and Sales are not yet runtime systems. Their interfaces should remain fixtures/contracts until their owning implementations exist.
