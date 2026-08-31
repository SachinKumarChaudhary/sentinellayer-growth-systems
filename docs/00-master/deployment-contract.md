# SentinelLayer Deployment Contract

**Status:** Baseline  
**Scope:** All ten SentinelLayer systems

## Runtime contract
Every system MUST separate domain logic from its execution runtime.

Supported runtime classes:
- Local/Docker: reference development and self-hosted runtime.
- Managed web/API runtime: HTTP-facing services.
- Managed worker runtime: continuously running workers when required.
- Serverless/event runtime: short-lived scheduled or event-driven execution.

A runtime adapter may change process lifecycle, scheduling trigger, or transport implementation, but MUST NOT change business invariants.

## Configuration contract
- Configuration is supplied through environment variables or an equivalent secret/configuration manager.
- Production secrets MUST never be committed.
- Application variables use the SL_ prefix.
- Development defaults MUST be safe.
- Real external side effects are disabled unless an explicit production gate enables them.

## Database contract
Supabase/PostgreSQL is the canonical durable state layer.
- Schema changes are migrations.
- Transactions and database constraints protect consequential state transitions.
- Application retries MUST be idempotent.
- Workers use leases/claims for concurrent work.
- Derived data MUST be rebuildable.
- Systems MUST NOT silently mutate another system's domain-owned state.

## Job contract
A job MUST have stable identity, durable state, retry classification, attempt history where consequential, lease/claim semantics when concurrent execution is possible, terminal states, and safe recovery after worker termination.
 No job runner may assume process memory is durable.

## Provider contract
External providers are adapters behind interfaces.
- Normalize accepted, retryable failure, permanent failure, and ambiguous outcome.
- Provider adapters MUST NOT decide business eligibility.
- Mail credentials and provider-specific behavior remain isolated from campaign policy.

## Event contract
Significant cross-system events use the canonical envelope defined in system-contracts.md.
At minimum: event_id, event_type, occurred_at, source_system, environment, correlation_id, schema_version, domain identifiers when known, and structured payload.
Never put secrets into event payloads.

## Health contract
Every deployable service MUST expose an operational health mechanism appropriate to its runtime.
- Liveness: process/runtime is alive.
- Readiness: required dependencies/configuration are usable.
- Health checks MUST NOT perform consequential external actions.
- Mail health checks MUST NOT send email.
HTTP health endpoints may be supplied by a runtime adapter rather than domain logic.

## Observability contract
Every deployable component MUST provide structured logs, worker/service identity, environment, correlation identifiers for consequential operations, error classification, and startup/shutdown records.
Sensitive credentials and unnecessary personal data MUST NOT be logged.

## Security contract
- Secrets stay outside source control.
- Production and non-production credentials are separated.
- Least privilege is the default.
- Suppression, authorization, and safety gates fail closed.
- Consequential administrative changes are auditable.

## Environment contract
Minimum environments: development -> staging -> production.
Development uses mock/synthetic external side effects. Staging uses controlled synthetic identities. Production enables real side effects only after the production gate passes.

## Portability contract
The same domain behavior MUST be executable through local process/Docker, a conventional managed worker/container, and a serverless/event-driven adapter where workload constraints permit.
Portability means identical state and safety semantics, not identical infrastructure.

## Deployment gate
- Unit tests pass
- Integration tests pass
- Concurrency tests pass
- Image builds reproducibly
- Configuration validation passes
- Health/readiness checks work
- Shutdown/restart recovery is tested
- Idempotency is tested
- Suppression/reply-stop is tested
- Provider failure paths are tested
- Staging synthetic flow completes
- Rollback is documented
- Real side effects are explicitly enabled

## Current reference implementation
The existing mail engine is the reference implementation for deterministic Python orchestration, Supabase/PostgreSQL state, atomic claiming and leases, idempotency, retry classification, ambiguous delivery handling, provider abstraction, SMTP integration, and safe configuration.
Future systems should conform to this contract rather than copy implementation details.