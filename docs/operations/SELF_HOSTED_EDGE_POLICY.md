# Self-Hosted Edge Policy

Owner: Operations
Target: self-hosted laptop
Status: Ready for implementation once Tracking HTTP contract is merged

## Boundary
The reverse proxy is the only public HTTP entrypoint. Application containers remain on an internal Docker network and are never published directly.

## Baseline controls

| Control | Baseline |
|---|---|
| Public HTTP | HTTPS only |
| Request body | 32 KiB maximum for tracking ingestion |
| Request timeout | 10 seconds |
| Keepalive | bounded |
| Concurrent upstream requests | 32 |
| Per-source rate | 30 requests/minute |
| Per-source burst | 10 |
| Rate-limit response | HTTP 429 |
| Proxy-to-app network | private Docker network |
| Administrative endpoints | not public |

The values must be load-tested and may be changed by deployment configuration before production. They must not be embedded into Tracking business logic.

## Identity and abuse
The edge must not trust client-supplied identity headers such as X-Forwarded-For unless they are set/overwritten by a trusted proxy boundary.

Source identity must be derived from the trusted network boundary. Token-level policy, if required by the final Tracking contract, is enforced in addition to—not instead of—the edge limits.

## Observability
Every throttle/rejection must produce an operational log containing:
- timestamp;
- endpoint;
- rejection reason;
- trusted source classification;
- request correlation identifier where available.

Never log credentials, tracking tokens, authorization headers, or request bodies.

## Failure behavior
When the edge or upstream is saturated:
- reject new work predictably;
- return an appropriate HTTP error;
- emit an operational signal;
- do not silently mutate or fabricate Tracking evidence.

## Validation
Before production:
1. normal traffic test;
2. burst test;
3. sustained-rate test;
4. concurrent-connection test;
5. oversized-body test;
6. upstream-down test;
7. restart/recovery test;
8. verify throttling is observable;
9. verify no secrets appear in logs.