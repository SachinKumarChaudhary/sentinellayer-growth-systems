# System Map

## Purpose
Authoritative map of SentinelLayer production systems and boundaries.

## Core lifecycle
Account Intelligence → Decision-Maker Intelligence → Buying Intent → Campaign / Message → RenderedSendTreatment → Mail / Deliverability → Tracking + Replies → Conversation Intelligence → Sales → Analytics / Learning.

Operations / Runtime provides deployment, observability, configuration, and operational controls across the lifecycle.

## Boundaries
- Intelligence produces AccountRef, PersonRef, IntentSnapshot.
- Campaign owns strategy, offers, messaging, CTA, sequences, experiments, enrollment, and deterministic treatment resolution; it produces RenderedSendTreatment.
- Mail owns queueing, claiming, leases, SMTP/provider execution, retries, and durable send state; it produces ProviderOutcome.
- Tracking captures and normalizes behavioral events; it produces TrackingEvent.
- Conversation owns reply ingestion, classification, and conversation state; it produces ConversationHandoff.
- Sales owns commercial handoff and opportunity state; it produces SalesHandoff.
- Analytics owns attribution and derived reporting.
- Platform owns shared contracts, schemas, cross-system primitives, validation, and integration tests.
- Operations owns runtime/deployment/observability/control-plane concerns.

## Non-negotiable boundaries
- Campaign does not perform mail delivery.
- Mail does not implement campaign strategy.
- Analytics is derived state, not canonical operational state.
- AI/Hermes is bounded by system contracts and does not own durable business state.
- n8n is an integration/automation edge, not the authoritative state machine.
- Supabase/PostgreSQL is the canonical durable state layer.
- Python is the deterministic execution layer where execution logic is required.

Cross-system dependencies use documented contracts, never private implementation details.
