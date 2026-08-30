# Agent Instructions

## Mission
Build the SentinelLayer outbound growth engine as production-grade software.

## Hard rules

- Never send real prospect email during development or CI.
- Never commit secrets, passwords, SMTP credentials or API keys.
- Use synthetic data and MockMailProvider for tests.
- Supabase is the durable operational state layer.
- Python owns deterministic campaign orchestration.
- Hermes is an AI subsystem, not the state machine.
- n8n is integration glue, not the campaign brain.
- Suppression and reply-stop checks fail closed.
- Every send requires idempotency.
- Provider adapters must be interfaces; do not hard-code a vendor.
- Use UTC internally; apply mailbox/campaign timezone for scheduling windows.
- Schema changes must be migration-based.
- Add tests for state transitions and failure paths.
- Do not weaken tests to make failures disappear.
- Real provider support stays disabled until an explicit production gate.

## Required engine components

1. Configuration/settings
2. Database repository layer
3. Campaign state machine
4. Eligibility policy
5. Scheduler
6. Atomic send claimant
7. Provider interface
8. MockMailProvider
9. SMTP adapter
10. IMAP adapter
11. Retry/idempotency handling
12. Suppression and bounce handling
13. Mailbox health/warmup policy
14. Inbound reply processor
15. Structured logging
16. Health/metrics
17. Worker entrypoints
18. Automated tests

## Quality gates

- unit tests pass
- integration tests pass against an isolated test database
- lint passes
- type checking passes
- no secrets detected
- idempotency tests pass
- suppression tests pass
- reply-stop tests pass
- concurrent claiming tests pass
- retry/provider failure tests pass

## Implementation order

Build the smallest vertical slice first:
configuration -> repository -> eligibility -> atomic claim -> MockMailProvider -> send state transition -> tests.

Then add retries, inbound processing, health controls, real SMTP and IMAP adapters.

Do not implement production SMTP sending before the mock vertical slice is proven.
