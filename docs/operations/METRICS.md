# Operational Metrics

SentinelLayer now has a dependency-free `OperationalMetrics` registry and a structured operational-event emitter in `sentinellayer_growth_engine.metrics`.

## Design

- Process-local counters and gauges are deterministic and thread-safe.
- `snapshot()` returns stable JSON-compatible data for health/operator adapters.
- `emit_event()` writes one JSON object per log record through the `sentinellayer.operations` logger.
- Core runtime code does not depend on Prometheus, OpenTelemetry, or a hosted observability service.
- Provider credentials, message bodies, recipient addresses, and other secrets must never be passed as event fields.

## Required runtime signals

The production integration should instrument at least:

| Signal | Type | Operational use |
| --- | --- | --- |
| `scheduler.tick` | event | worker heartbeat/liveness |
| `mail.claimed` | counter | queue throughput |
| `mail.sent` | counter | successful delivery handoff |
| `mail.failed` | counter | provider/error alerting |
| `mail.suppressed` | counter | safety enforcement |
| `conversation.inbound` | counter | inbound activity |
| `conversation.failed` | counter | inbound processing alerting |
| `queue.depth` | gauge | backlog detection |
| `worker.last_success_epoch` | gauge | stale-worker detection |

The registry is intentionally only the instrumentation boundary. A later deployment can export the same snapshot/events to Prometheus, OpenTelemetry, or a hosted log/alerting system without changing domain behavior.

## Alert policy

At minimum, production alerting should cover:

1. Worker heartbeat stale beyond the configured operating window.
2. Repeated mail-provider failures.
3. Growing send queue without successful sends.
4. Repeated inbound-processing failures.
5. Any unexpected attempt to operate real email outside the protected production environment.

Metrics do not replace the existing fail-closed production gate; they provide evidence and detection around it.
