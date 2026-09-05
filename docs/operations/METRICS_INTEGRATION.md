# Metrics Integration Checklist

The metrics registry is an instrumentation boundary, not a claim that production alerting is already deployed.

## Instrumentation points

- Scheduler loop: increment `scheduler.tick` and update `worker.last_success_epoch` after a successful cycle.
- Send claim: increment `mail.claimed`.
- Successful provider handoff: increment `mail.sent`.
- Provider/transport failure: increment `mail.failed` and emit a classified failure event.
- Suppression/stop decision: increment `mail.suppressed`.
- Inbound message accepted: increment `conversation.inbound`.
- Inbound processing failure: increment `conversation.failed`.
- Queue inspection: set `queue.depth`.

## Export boundary

The runtime may expose `OperationalMetrics.snapshot()` through an authenticated operator endpoint or a future Prometheus/OpenTelemetry adapter. Do not add an unauthenticated public metrics endpoint merely to satisfy observability requirements.

## Alert evidence required before production activation

Record at least one successful test for each alert class:

- stale worker
- repeated SMTP/provider failure
- growing send backlog
- repeated IMAP/conversation failure
- unsafe real-email configuration

The evidence should contain timestamps and safe classifications, not credentials or message content.
