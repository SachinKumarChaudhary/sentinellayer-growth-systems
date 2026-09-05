# Operations Metrics Specification

## Runtime telemetry

The self-hosted runtime must expose or collect:
- service health/readiness
- process restart count
- queue depth/backlog when available
- provider failure counts when available
- database connectivity failures
- HTTP 4xx/5xx and latency
- rate-limit rejection count
- release version/commit
- safety-control state changes

## Implementation boundary

Operations owns collection, transport, dashboards, alert routing, and retention of operational telemetry.

Domain systems own the semantics and thresholds for their signals.

## Minimum local implementation

Container stdout/stderr remains the primary log transport. Logs must be structured enough to correlate service, environment, release, request/event correlation, and severity without exposing secrets.

Local metric collection may be added with a lightweight self-hosted collector after endpoint contracts are available. Do not introduce a second business-state database.

## Alerts

Infrastructure-only alerts may be configured immediately:
- service unavailable
- readiness failing
- repeated container restart
- sustained HTTP 5xx
- database unavailable
- disk/resource exhaustion when observable
- outbound control state entering SAFE_STOP

Domain-specific thresholds require owner approval from Mail, Tracking, Campaign, etc.
