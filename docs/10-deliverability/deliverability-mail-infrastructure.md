# Deliverability & Mail Infrastructure

**Status:** Architecture baseline  
**Scope:** System 10 — Deliverability & Mail Infrastructure  
**Authority:** This document defines the mail transport and deliverability boundary. It must remain consistent with `docs/00-master/system-contracts.md`, `docs/00-master/shared-contracts.md`, `docs/00-master/integration-contracts.md`, and `docs/00-master/deployment-contract.md`.

## 1. Purpose

This system is responsible for reliable outbound mail execution and the infrastructure controls surrounding delivery. It is **not** responsible for campaign strategy, lead selection, message generation, or sales decisions.

Its job is to turn an already-approved send treatment into a durable, observable provider transaction while preserving safety under retries, concurrency, process failure, and ambiguous provider outcomes.

## 2. Boundary

### Upstream

The Campaign/Message system supplies the validated `RenderedSendTreatment` / send request.

The mail system MAY enforce transport and operational safety constraints, but MUST NOT silently rewrite campaign strategy.

### Downstream

The system communicates with configured mail providers and records normalized provider outcomes.

Tracking and conversation systems consume durable events/results; they do not control SMTP execution.

## 3. Canonical execution flow

```
RenderedSendTreatment
        |
        v
eligibility + suppression gate
        |
        v
durable send queue
        |
        v
atomic claim + lease
        |
        v
provider adapter
        |
        v
SMTP submission
        |
        +--> accepted
        +--> retryable failure
        +--> permanent failure
        +--> ambiguous outcome
        |
        v
durable state + attempt history
        |
        v
events / reconciliation / tracking
```

A worker crash must never make process memory the source of truth.

## 4. Durable state invariants

Every consequential send has a stable identity and durable lifecycle state.

The system MUST preserve:

- idempotent send identity
- deterministic Message-ID where required by the send contract
- atomic work claiming
- lease ownership and expiry
- attempt history
- normalized provider outcome
- retry scheduling
- terminal state
- recovery from worker termination
- suppression/reply-stop enforcement before execution

Two concurrent workers MUST NOT intentionally claim the same send at the same time.

A timeout after provider submission is **not equivalent to a confirmed failure**. It enters the ambiguous/reconciliation path rather than being blindly retried.

## 5. Provider abstraction

Provider-specific behavior lives behind an adapter.

The adapter normalizes transport results into the shared provider-outcome contract:

- `accepted`
- `retryable_failure`
- `permanent_failure`
- `ambiguous`

The provider adapter owns SMTP connection/authentication/transport details. Business eligibility remains outside it.

Current reference transport: authenticated SMTP submission, including Hostinger-compatible port 587/465 configuration.

Port 25 is not required by the architecture.

## 6. Retry policy

Retry decisions MUST be based on normalized outcome and error classification, not merely on exceptions.

Examples:

- transient connection failure → retryable
- provider 4xx response → normally retryable, subject to provider-specific classification
- invalid recipient / permanent 5xx → permanent
- post-submit timeout / lost response → ambiguous
- policy/suppression violation → do not retry

Retries MUST preserve idempotency and MUST NOT create an uncontrolled duplicate-send loop.

## 7. Ambiguous delivery

The most dangerous failure is:

```
provider may have accepted mail
        +
worker does not receive confirmation
```

The system MUST represent this explicitly.

It MUST NOT convert every timeout into `failed` and immediately resend.

Resolution may use provider evidence, durable Message-ID correlation, attempt records, reconciliation, or an explicit operator policy.

Until resolved, ambiguous sends are treated conservatively.

## 8. Deliverability controls

The platform should support, at minimum:

- domain/mailbox identity
- provider configuration
- per-mailbox and per-domain sending limits
- scheduling windows
- bounce/complaint/suppression state
- reply-stop enforcement
- authentication/configuration validation
- delivery and failure telemetry
- provider health
- mailbox/domain pause controls

These controls protect sender reputation but MUST NOT be confused with guarantees of inbox placement.

Inbox placement depends on factors outside the application, including recipient-provider filtering and sender/domain reputation.

## 9. Domain and mailbox readiness

Before enabling production sending, validate the configured sending identity and provider credentials.

The production checklist should cover the relevant DNS/authentication records for the chosen mail provider, mailbox authentication, sender identity consistency, and provider-specific limits.

The application MUST fail closed when required production configuration is missing or invalid.

## 10. Inbound mail boundary

Inbound processing is a separate transport concern from outbound SMTP.

Where inbound mail is required, an adapter should retrieve messages through the supported provider mechanism (for example IMAP or a provider webhook/API), normalize them, and hand them to the Conversation Intelligence boundary.

The outbound worker MUST NOT become the inbound conversation engine.

## 11. Tracking boundary

Delivery infrastructure may emit durable delivery/transport events.

Open and click tracking are separate signals and MUST NOT be represented as proof of human engagement or inbox placement.

Tracking identifiers must be opaque and must not expose secrets.

## 12. Security

- SMTP credentials are secrets and never enter source control or logs.
- Production and staging credentials are separate.
- Least privilege is required wherever the provider supports it.
- Secrets must not be included in events, exception messages, or metrics.
- Administrative mailbox/domain changes must be auditable.
- Suppression and safety gates fail closed.

## 13. Runtime portability

The mail domain logic MUST remain independent of its execution host.

Supported deployment shapes:

```
Local/Docker
    |
Render / conventional worker
    |
Customer-hosted Docker
    |
serverless adapter where workload/CPU/network constraints permit
```

The runtime may change scheduling and lifecycle mechanics, but MUST preserve database state, idempotency, leases, retries, and safety invariants.

Cloudflare is an optional transport/runtime adapter, not a reason to couple the core engine to Cloudflare-specific APIs.

## 14. Current implementation status

### Implemented/reference

- Python worker
- Supabase/PostgreSQL durable state
- send claiming and leases
- uncertain-send state
- reconciliation function
- provider abstraction
- SMTP transport
- retry classification
- eligibility gate
- deterministic IDs
- unit tests
- Supabase concurrency integration tests
- CI test/integration workflows
- Docker image

### Still required before production-grade activation

- controlled real-provider staging smoke test
- production DNS/mailbox readiness verification
- operational metrics/alerts
- explicit mailbox/domain rate-limit configuration
- inbound adapter if required by the product flow
- provider-specific bounce/complaint ingestion where available
- reconciliation evidence and operator tooling
- deployment/runtime smoke tests
- production rollback procedure
- final end-to-end test across Campaign → Send → Tracking/Conversation boundaries

This section must be updated as implementation progresses.

## 15. Production gate

Real outbound sending is enabled only when:

1. CI is green.
2. Supabase concurrency tests are green.
3. Docker build is reproducible.
4. Production configuration validates.
5. SMTP authentication is validated against a controlled mailbox.
6. Suppression/reply-stop is tested.
7. Duplicate-send/idempotency behavior is tested.
8. Retry and ambiguous-send paths are tested.
9. Domain/mailbox readiness is verified.
10. Monitoring and rollback are available.
11. A controlled synthetic end-to-end send succeeds.

## 16. Non-goals

This system does not:

- choose prospects
- decide who should receive a campaign
- generate campaign strategy
- generate AI copy
- qualify leads
- conduct sales conversations
- claim guaranteed inbox placement
- bypass provider anti-abuse controls

Those responsibilities remain with their respective systems.

## 17. Design principle

**The mail infrastructure must make a send boring.**

Once a valid send treatment reaches this boundary, execution should be deterministic, durable, observable, recoverable, and provider-independent.

The hardest correctness property is not throughput. It is avoiding an unintended duplicate while correctly recovering from failures that occur after a provider may already have accepted a message.
