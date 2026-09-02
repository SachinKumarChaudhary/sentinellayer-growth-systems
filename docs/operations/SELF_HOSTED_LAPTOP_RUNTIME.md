# Self-Hosted Laptop Runtime Contract

**Status:** Active Operations design  
**Target:** Self-hosted laptop production runtime

## Purpose

Define the runtime boundary for SentinelLayer when the production control plane is hosted on an owner-controlled laptop. This contract is operational; it does not redefine Campaign, Mail, Tracking, or Platform business contracts.

## Runtime topology

```
Internet
  |
  v
[Router / firewall / port forwarding]
  |
  v
[HTTPS reverse proxy / edge]
  |---- rate limiting
  |---- request-size / connection limits
  |---- TLS termination
  |---- access logging
  |
  +--> Tracking HTTP ingestion
  |
  +--> future operational HTTP endpoints
  |
[Docker services]
  +--> SentinelLayer Python worker
  +--> runtime support services as explicitly approved
          |
          v
      Supabase/PostgreSQL
```

The Python mail worker is not itself an Internet-facing HTTP server. Tracking owns tracking-event semantics; Operations owns the network/runtime boundary.

## Laptop requirements

- dedicated OS user/account for the deployment;
- Docker Engine/Compose available;
- host firewall enabled;
- automatic security updates where operationally safe;
- prevent sleep/hibernation while production is active;
- stable network connection;
- stable power source; UPS is strongly preferred;
- encrypted host storage;
- authenticated OS access;
- backup destination independent of the laptop;
- time synchronization enabled.

A laptop outage is an availability event. Durable business state must remain in Supabase; local containers must be disposable.

## Network boundary

Do not expose the Python worker directly to the public Internet.

Only the reverse proxy/edge may publish approved HTTP ports. The edge must enforce:

- HTTPS/TLS;
- maximum request body size;
- connection/read/write timeouts;
- rate limiting;
- bounded concurrent connections;
- access/error logs without credentials;
- upstream health failure handling.

Administrative endpoints must not be publicly exposed by default.

## Tracking rate-limit baseline

Until domain-specific traffic requirements are finalized, Operations should use a conservative configurable baseline rather than hard-code a business policy.

Required configuration dimensions:

- requests per source over a rolling interval;
- burst allowance;
- maximum concurrent requests;
- maximum body size;
- upstream timeout;
- rejection status;
- metrics/log event for throttling.

The edge must fail closed under resource exhaustion. It must not silently drop evidence without an operational signal.

The exact production limits are a deployment configuration decision and must be load-tested before activation.

## Service lifecycle

Every container must:

- have deterministic image/version;
- restart according to an explicit policy;
- expose health/readiness behavior where applicable;
- receive SIGTERM and shut down gracefully;
- have bounded resource consumption;
- write structured logs to an operationally controlled destination.

The mail worker already provides PostgreSQL readiness checking and graceful shutdown.

## Real-email safety

Development/staging:
- `SL_REAL_EMAIL_ENABLED=false`;
- synthetic recipients only;
- production SMTP credentials unavailable.

Production:
- production environment explicitly selected;
- SMTP credentials injected outside source control;
- real-email gate explicitly enabled;
- human production approval recorded.

A laptop restart must never convert a disabled environment into an enabled one.

## Recovery model

Supabase is the durable state layer. Container-local state is disposable.

Recovery sequence:

1. isolate failed host/runtime;
2. preserve logs and release identity;
3. verify Supabase/database health;
4. restore the last known-good image;
5. validate configuration;
6. run health/readiness checks;
7. run synthetic smoke checks;
8. reconcile mail queue state before resuming delivery;
9. restore traffic gradually;
10. record the incident.

Never blindly replay an outbound queue after a laptop restart or network failure.

## Operational checks

Before production activation:

- host firewall verified;
- sleep/hibernation disabled;
- Docker restart policy verified;
- reverse-proxy TLS verified;
- rate-limit/load test passed;
- backup restore test passed;
- service restart test passed;
- laptop reboot recovery test passed;
- network interruption test passed;
- mail idempotency/concurrency tests passed;
- global kill switch tested;
- production-send gate tested.

## Explicit non-goals

This document does not define:

- campaign strategy;
- message content;
- tracking evidence interpretation;
- SMTP retry classification;
- buying intent;
- analytics attribution;
- shared database schemas.

Those remain owned by the appropriate subsystem.
