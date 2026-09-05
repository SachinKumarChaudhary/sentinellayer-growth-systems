# Observability Specification

## Scope

Operations owns runtime telemetry for the self-hosted laptop. Domain systems remain owners of domain semantics and thresholds.

## Canonical signals

- service liveness/readiness
- deployment version/commit
- worker starts/stops/restarts
- queue depth/backlog where exposed by Mail
- provider failures where exposed by Mail
- database connectivity
- HTTP request status/latency
- edge throttling/rejections
- critical safety-control state changes

## Log rules

Structured logs must include a timestamp, service, severity, event name, and correlation identifier where available.

Never log:
- passwords
- API keys
- SMTP credentials
- database URLs
- authorization headers
- tracking tokens
- raw request bodies

## Alert ownership

Operations owns routing, suppression, acknowledgement, and incident handling.

Domain owners provide domain thresholds and interpretation:
- Mail: provider/bounce/complaint/queue thresholds
- Tracking: ingestion/error/throttle thresholds
- Platform: contract/integration failures
- Campaign: campaign execution failures

Until domain thresholds are approved, only infrastructure-level alerts are enabled.
