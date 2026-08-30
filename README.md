# SentinelLayer Growth Systems

Production growth infrastructure for SentinelLayer.

## Current build target

Outbound email/campaign engine:

Leads -> Campaigns -> Scheduler -> Mail Provider -> Events -> Replies -> Hermes -> Sales

- Supabase: durable operational state and database.
- Python engine: campaign orchestration, scheduling, eligibility, rate limits, retries, idempotency, provider adapters and inbound processing.
- Hermes: AI classification, intent extraction, cached personalization and response drafting.
- n8n: integration glue, not campaign orchestration.
- GitHub Actions: automated quality gates.

## Development boundary

Development uses synthetic leads and a mock mail provider. Real outbound domains, mailboxes and prospect email are deferred until automated tests and end-to-end simulation pass.

## Principles

1. Suppression and safety rules fail closed.
2. Every send is idempotent.
3. Database state transitions are transactional.
4. Provider credentials never enter source control.
5. Schema changes are migration-based.
6. AI does not own deterministic campaign state.
7. Real sending is never the default configuration.
