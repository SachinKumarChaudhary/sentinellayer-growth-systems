# Platform Execution Plan

## Phase 1 — Contract foundation
Maintain schemas, validate them in CI, validate representative payloads at runtime, and fail closed on invalid data.

## Phase 2 — Cross-system identity
Standardize account/person/campaign/enrollment/send identifiers and correlation propagation; test identity preservation.

## Phase 3 — Event contracts
Standardize event envelope, producer/consumer, timestamp, correlation, payload, and immutable event identity requirements.

## Phase 4 — Boundary integration
Campaign Resolver → RenderedSendTreatment → SendRequest → Mail; ProviderOutcome → Tracking/Conversation; ConversationHandoff → SalesHandoff; canonical outcomes → Analytics.

## Phase 5 — Supabase integration
Verify real-database constraints, RLS policies, concurrency/idempotency invariants, and synthetic lifecycle tests.

## Phase 6 — Production gate
Unit tests, contract tests, integration tests, real Supabase tests, concurrency tests, green CI, no unresolved contract violations, and no secrets in Git.
