# Tracking HTTP Abuse Controls

## Ownership boundary

- **Edge / Operations:** request-rate limiting, concurrent-connection limits, request-size limits, timeouts, rejection observability, and runtime saturation behavior.
- **Tracking application:** token resolution, tracking-event semantics, automation classification, and durable evidence behavior.
- **Platform:** shared HTTP/runtime contract compatibility.

The edge must not invent or modify tracking-event identity, idempotency, or classification semantics.

## Self-hosted production policy

The self-hosted Nginx edge applies controls to `/t/` before requests reach Tracking:

| Control | Policy | Failure behavior |
|---|---|---|
| Per-source request rate | 30 requests/minute | Excess burst is rejected with `503` |
| Per-source burst | 10 requests, `nodelay` | Burst above configured allowance is rejected |
| Per-source concurrent connections | 32 | Excess connections are rejected with `503` |
| Request body size | 32 KiB | Oversized request is rejected with `413` |
| Header timeout | 10s | Slow header clients are bounded |
| Body timeout | 10s | Slow request bodies are bounded |
| Upstream connect timeout | 2s | Upstream failure fails safely |
| Upstream read/send timeout | 10s | Hung upstream requests are bounded |

The policy is keyed to the network source (`$binary_remote_addr`). Client-supplied identity headers are forwarded only as application metadata and are **not** used to establish the abuse-control identity.

Opaque tracking tokens are deliberately absent from the Nginx access-log request line. Operational logs retain timestamp, request ID, source address, method, status, byte count, request duration, and upstream duration.

## Saturation behavior

A healthy request should continue to reach Tracking while abusive traffic is bounded at the edge. A saturated edge must reject excess traffic rather than queue an unbounded workload or bypass Tracking's semantic validation.

`503` is the operational signal for Nginx rate/connection rejection. `413` identifies request-size enforcement. Upstream timeout/failure is surfaced as a bounded gateway failure rather than an unbounded connection.

## Validation

The production configuration is validated through the repository's Operations CI safety gate. The isolated behavioral harness at `scripts/selfhosted/test_edge_behavior.sh` exercises the same control classes against a dedicated Compose edge configuration and proves:

- normal tracking GET/POST remains available;
- burst traffic is rate limited;
- concurrent connections are capped;
- oversized requests are rejected;
- upstream timeout is surfaced;
- restart/recovery restores service;
- rejection is observable;
- opaque tokens, request bodies, and credential-like material are absent from edge logs.

The behavioral workflow is push-triggered and runs on changes to `ops/nginx/**`, the behavioral harness, or its workflow definition.

## Deployment procedure

1. Supply the production `.env` outside Git.
2. Run `scripts/selfhosted/deploy.sh` with the production Compose file and environment file.
3. Confirm Compose configuration validation succeeds.
4. Confirm Nginx is the only public HTTP edge and Tracking is not directly published.
5. Confirm `/healthz` and `/readyz` are healthy before enabling outbound execution.
6. Review edge rejection status counts and request-duration/upstream-duration telemetry after rollout.
7. If rejection rates unexpectedly increase, inspect source concentration and upstream health before increasing limits. Do not disable the edge controls as the first response.

The deployment helper intentionally refuses to proceed when real outbound email is enabled without the separate production gate.

## Configuration separation

`ops/nginx/selfhosted.conf` is the self-hosted production-target configuration. `ops/nginx/test.conf` is an isolated behavioral-test configuration with intentionally shorter timeouts and a test upstream. Test settings must not be copied into production merely to make tests pass.

Any change to rate, burst, connection, size, or timeout policy must update this runbook and the behavioral assertions in the same change.
