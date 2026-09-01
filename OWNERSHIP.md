# Repository Work Ownership

This repository is developed by multiple parallel ChatGPT sessions/agents. This document defines ownership boundaries to prevent conflicting implementation.

## Ownership

### Campaign / Messaging Session

Owns:
- `docs/01-campaigns/`
- campaign strategy
- offer definitions and versions
- message definitions and versions
- CTA definitions and versions
- sequence definitions and versions
- experiments and variants
- campaign enrollment
- Campaign Resolver
- campaign/message rendering
- campaign-specific migrations and tests

The Campaign system produces `RenderedSendTreatment`. It does not send mail.

### Deliverability / Mail Infrastructure Session

Owns:
- deliverability and mail-infrastructure documentation
- SMTP/provider abstraction
- mailbox/provider configuration
- durable send state
- queue claiming
- worker leases/reclaim
- idempotency
- retry classification
- ambiguous-delivery handling
- mail execution
- send-related migrations and tests
- production mail runtime

The Mail Engine consumes a validated send contract and owns delivery execution.

### Platform / Cross-System Session

Owns:
- `docs/00-master/`
- `schemas/`
- shared contract validation
- `tests/contracts/`
- cross-system integration tests
- shared event/envelope contracts
- system-wide identity/correlation contracts
- integration test harnesses

This session does not implement Campaign business logic or Mail delivery logic.

### Tracking Session

Owns:
- behavioral tracking implementation
- tracking ingestion
- link/event processing
- tracking-specific storage and migrations
- tracking-specific tests

### Conversation Intelligence Session

Owns:
- reply ingestion
- conversation/thread state
- reply classification
- conversation intelligence
- conversation handoff

### Sales Session

Owns:
- sales handoff
- opportunity/deal state
- sales workflow state
- sales-specific automation

### Analytics Session

Owns:
- attribution
- derived metrics
- campaign/revenue analytics
- reporting models

### Operations / Runtime Session

Owns:
- deployment/runtime configuration
- health/readiness
- observability
- operational controls
- environment configuration
- deployment-specific infrastructure

## Conflict Rules

1. **One owner per implementation area.** Do not modify another session's implementation merely because a dependency is inconvenient.
2. **The repository is the source of truth.** Always fetch the current file before modifying it.
3. **Never overwrite stale work.** Updates must use the current Git blob SHA.
4. **Never rewrite an applied database migration.** Add a new migration instead.
5. **Keep commits small and scoped.** A commit should represent one coherent change.
6. **Do not force-push or rewrite shared history.**
7. **Shared contract changes require coordination.** A producer and consumer must agree on the change, schema/version implications must be explicit, and an integration test must cover the boundary.
8. **Do not duplicate domain logic across systems.** If a capability belongs to another owner, expose or consume a contract instead.
9. **Tests must respect ownership.** Domain tests belong with the domain; cross-domain behavior belongs in the platform integration suite.
10. **No secrets in Git.** Credentials, API keys, mailbox passwords, provider secrets, and private tokens must remain in the approved secret/configuration mechanism.

## Shared Interface Change Protocol

For a change crossing system boundaries:

```
Proposal
  ↓
Identify producer + consumer
  ↓
Review existing contract
  ↓
Decide compatibility / schema version
  ↓
Update schema
  ↓
Update producer
  ↓
Update consumer
  ↓
Add integration test
  ↓
Run full CI gate
```

Example:

```
Campaign Resolver
      ↓
RenderedSendTreatment
      ↓
Mail Engine
```

Campaign may change the treatment only through the agreed contract. Mail may reject an invalid treatment, but it must not implement campaign strategy logic.

## Database Migration Protocol

- Use uniquely timestamped migration filenames.
- A migration that has been applied is immutable.
- Scope migrations to the owning subsystem where possible.
- Cross-system tables require coordination.
- Foreign keys and shared identifiers must be documented in the relevant contract.
- Production database changes require the repository's existing migration/test gates.

## Branch / Commit Guidance

Preferred:

```
main
├── campaign/*
├── platform/*
├── mail/*
├── tracking/*
└── operations/*
```

If separate branches are not practical, enforce ownership through file boundaries and current-SHA updates.

Recommended commit style:

```
feat(campaign): implement deterministic treatment resolver
feat(platform): add cross-system contract
test(integration): validate campaign-to-mail boundary
fix(mail): preserve provider outcome semantics
```

## Current Priority

The current platform sequence is:

```
Shared schemas + validation
        ↓
Campaign Resolver
        ↓
RenderedSendTreatment
        ↓
Mail-engine boundary adapter
        ↓
Campaign → Mail integration tests
        ↓
Supabase-backed end-to-end tests
        ↓
Full lifecycle verification
```

The Campaign session owns the Resolver. The Platform session owns the boundary and cross-system verification. The Mail session owns delivery execution.
