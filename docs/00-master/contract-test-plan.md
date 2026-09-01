# Cross-System Contract Test Plan

## Goal
Prove that the ten systems can evolve independently without breaking the interfaces defined in `system-contracts.md` and `shared-contracts.md`.

## Test layers

### 1. Schema validation
Every JSON contract has positive and negative fixtures.

Test:
- required fields
- types
- enum values
- timestamps
- email format where applicable
- additional-property policy
- schema version

### 2. Unit boundary tests
Each producer validates what it emits. Each consumer rejects invalid input deterministically.

### 3. Integration tests
Use Supabase/PostgreSQL and the real repositories/services with external mail replaced by a mock provider.

### 4. Concurrency tests
Run multiple workers against the real PostgreSQL/Supabase test environment.

Prove:
- one queue item has one effective claim
- lease expiry permits reclaim
- successful send cannot be duplicated by retry
- suppression wins over concurrent scheduling

### 5. End-to-end synthetic lifecycle
Synthetic account → person → intent → campaign enrollment → rendered treatment → send request → mock provider outcome → tracking/reply → conversation → sales handoff → attribution.

## Required fixtures

### Happy path
- qualified P1 account
- two decision makers
- fresh intent evidence
- active campaign
- valid treatment
- provider accepted
- positive reply
- meeting booked
- opportunity created
- won outcome

### Negative paths
- invalid person
- no login/qualification upstream
- P4
- negative fit cap
- retired campaign version
- missing personalization evidence
- unresolved template variable
- suppressed email
- prior reply
- paused campaign
- paused mailbox
- provider timeout
- ambiguous provider outcome
- duplicate provider event
- duplicate reply
- invalid Hermes JSON

## Required assertions

### Identity preservation
`account_id`, `person_id`, `campaign_id`, `enrollment_id`, and `send_id` must remain consistent across all events/handoffs.

### Version preservation
Every send can be traced to exact strategy, offer, message, CTA, sequence and experiment versions.

### Safety
- suppression prevents send
- reply prevents future cold follow-up
- invalid treatment never reaches provider
- ambiguous provider outcome never causes an unsafe blind resend
- global pause prevents new claims

### Attribution
A won opportunity must retain the campaign and strategy versions that generated the originating enrollment/send path.

## CI gates

Every pull request touching contracts, campaign code, mail engine, tracking, conversation, sales, or analytics must run:

1. schema validation
2. unit tests
3. repository integration tests
4. contract tests for affected boundaries
5. concurrency suite for mail queue changes
6. type checking
7. linting

A contract-breaking change requires an explicit schema-version change and migration/update of all consumers.

## Production readiness

Before enabling real sending:
- all contract tests green
- real Supabase integration gate green
- concurrent-worker gate green
- synthetic 1,200-lead campaign simulation green
- no unresolved P0/P1 contract defects
- production control gates verified
