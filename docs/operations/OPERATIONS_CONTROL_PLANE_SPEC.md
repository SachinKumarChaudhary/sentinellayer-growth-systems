# Operations / Control Plane Specification

## Mission
Keep every SentinelLayer system deployable, observable, secure, recoverable, and controllable in development, staging, and production.

Operations governs runtime and delivery mechanics. It does not own campaign strategy, mail delivery logic, tracking interpretation, conversation classification, sales logic, or analytics business rules.

## Owns
- CI/CD pipelines and reusable GitHub Actions workflows
- build, test, lint, type-check, security, and release gates
- environment promotion and deployment automation
- runtime configuration and configuration validation
- secret references and secret-injection conventions
- service health/readiness/liveness
- structured operational logging and metrics conventions
- alerting and incident response
- global/campaign/mailbox emergency controls
- deployment rollback and recovery procedures
- backup/restore procedures for operational data
- operational audit records
- release/version management
- production readiness gates

## Does not own
- Campaign strategy, offers, messages, CTAs, experiments, enrollment, or resolver logic
- SMTP provider implementation, queue semantics, or mailbox delivery behavior
- Behavioral signal interpretation or intent scoring
- Reply classification or conversation meaning
- Sales qualification or opportunity business logic
- Analytics calculations or attribution business rules
- Shared domain contracts owned by Platform

## Runtime model

```text
Git push / PR
    -> CI validation
    -> artifact/build
    -> staging deployment
    -> readiness checks
    -> synthetic smoke test
    -> production approval gate
    -> production deployment
    -> post-deploy health verification
```

Real outbound email requires a separate explicit production-send gate. Development and CI must never enable real prospect delivery.

## Environment requirements

### Development
- mock provider by default
- synthetic identities/data
- no production secrets
- real-email flag must remain disabled

### Staging
- isolated environment and database
- synthetic/test recipients only
- representative integrations where safe
- production-like migrations and observability

### Production
- approved secrets/configuration
- real provider credentials
- explicit outbound-send enablement
- complete observability
- rollback path verified

## CI/CD ownership

Operations owns the pipeline; each system owns the tests that the pipeline executes.

Required baseline gates:
1. repository integrity / formatting checks
2. lint
3. type checking
4. unit tests
5. JSON Schema / contract tests
6. integration tests where configured
7. migration validation
8. secret/static-security checks
9. container build where applicable
10. deployment smoke/readiness checks

A failed required gate blocks promotion.

## Deployment contract

Every deployable service must provide:
- deterministic build
- immutable version identifier
- startup failure on invalid required configuration
- graceful shutdown
- readiness signal
- liveness/health signal where appropriate
- structured logs
- bounded retry behavior
- safe rollback strategy

Deployment must not silently run with missing safety configuration.

## Configuration and secrets

Configuration is externalized by environment. Secrets must never be committed to Git or embedded in images.

Use references/injection mechanisms for:
- database credentials
- provider credentials
- signing/encryption keys
- API tokens
- webhook secrets

The application must validate required configuration at startup and fail closed when an unsafe value is detected.

## Operational controls

Minimum controls:
- global outbound kill switch
- campaign pause/resume
- mailbox pause/resume
- production-send enable/disable gate
- deployment rollback
- maintenance mode where required

Controls must be auditable and protected by least privilege.

## Observability

Operations standardizes:
- structured logs with correlation IDs
- service health
- deployment version
- error rates
- queue/backlog health
- provider failures
- database connectivity
- migration status
- critical safety-state changes

Do not log secrets or raw authentication credentials. Avoid unnecessary sensitive payloads.

## Alert severity

### Critical
Immediate human response. Examples: global send safety failure, database corruption risk, uncontrolled duplicate-send risk, production service unavailable.

### High
Prompt human response. Examples: sustained provider failure, queue buildup, repeated worker crashes, abnormal bounce/complaint health signal.

### Medium
Operational follow-up. Examples: degraded non-critical dependency, rising latency, capacity approaching threshold.

### Low
Informational maintenance/diagnostic conditions.

## Incident workflow

```text
Detect
  -> classify severity
  -> contain
  -> preserve evidence
  -> diagnose
  -> recover
  -> verify health
  -> document root cause
  -> create preventive change
```

Safety containment takes priority over preserving throughput.

## Backup and recovery

Operations must maintain tested procedures for:
- database backup verification
- restore into isolated environment
- migration recovery
- configuration recovery
- service redeployment
- rollback to known-good application version

A backup that has never been restored is not considered verified recovery capability.

## Production readiness gate

Before enabling real outbound traffic:
- CI is green
- unit/contract/integration tests are green
- concurrency/idempotency tests are green for mail
- Supabase migrations are reproducible
- RLS/security review is complete
- configuration validation is tested
- observability is functioning
- kill switches are verified
- rollback is documented and exercised where practical
- staging synthetic end-to-end lifecycle passes
- mail provider/domain warm-up requirements are satisfied by the Mail system
- an explicit human approves production activation

## Ownership of safety decisions

Operations provides the control mechanism. The domain system provides domain-specific thresholds and decisions.

Example:

```text
Mail detects provider/bounce health issue
    -> Mail emits operational signal
    -> Operations routes/records/alerts it
    -> Mail policy may pause mailbox
    -> Operations provides override/kill control
```

Operations must not invent mail-domain logic merely to simplify implementation.

## Change management

Production changes should be:
- version controlled
- reviewed
- tested
- attributable to a commit/version
- reversible where practical

Emergency changes must still leave an audit trail and receive retrospective review.

## Definition of Done

An Operations change is complete when applicable documentation, workflow/configuration changes, tests, security validation, deployment validation, monitoring/alerts, rollback behavior, and handoff notes are complete and CI is green.
