# Platform Specification

## Mission
Provide stable, versioned, machine-enforceable interfaces so independently developed systems interoperate safely.

## Owns
- shared JSON Schemas and runtime validators
- canonical cross-system identifiers and correlation conventions
- event envelope conventions
- shared contract documentation
- cross-system integration tests
- genuinely cross-domain database primitives
- platform-level migration/security conventions

## Does not own
Campaign business logic, email copy/strategy, SMTP delivery, tracking logic, conversation classification, sales workflow, analytics business rules, or every domain table/migration.

## Guarantees
Fail-closed validation; explicit schema versions; deterministic identity/correlation; contractual idempotency; compatibility unless a breaking version is explicit; auditable lifecycle transitions; boundary test coverage.

## Contract registry
AccountRef, PersonRef, IntentSnapshot, CampaignEnrollment, RenderedSendTreatment, SendRequest, ProviderOutcome, TrackingEvent, ConversationHandoff, SalesHandoff, AttributionContext.

Machine-enforceable definitions live under `schemas/`.
