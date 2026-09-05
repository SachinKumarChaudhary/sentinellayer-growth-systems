# Operations Remaining Work

## Completed

- CI safety gate and least-privilege workflow permissions
- dependency audit
- Docker build/non-root validation
- runtime health/readiness
- release workflow
- self-hosted runtime design
- self-hosted edge/rate-limit policy
- static Nginx and Compose validation

## Still required

### 1. Metrics and alerts
Implement a local structured operational telemetry path for the self-hosted laptop. Minimum signals:
- worker health/restarts
- queue depth/backlog
- provider failures
- database connectivity
- HTTP 4xx/5xx
- rate-limit rejections
- release/version
- safety-control state changes

Do not invent domain thresholds. Mail/Tracking owners provide domain-specific thresholds.

### 2. Deployment adapter

Initial deployment and rollback scripts are now implemented under `scripts/selfhosted/`.
Create a reproducible self-hosted deployment command/path that:
- validates configuration;
- builds/pulls an immutable release;
- applies the approved Compose configuration;
- performs readiness checks;
- records deployed commit/version;
- fails without enabling real email.

### 3. Rollback / restore drills

Reproducible drill specifications are documented; execution remains staging-dependent.
Create reproducible staging procedures for:
- application rollback;
- host reboot recovery;
- network interruption;
- database backup verification;
- isolated restore;
- post-recovery queue reconciliation.

### 4. Production control plane
Implement the operational safety state model and administrative boundary for:
- global outbound kill switch;
- production-send enable gate;
- maintenance mode;
- campaign/mailbox pause overrides;
- auditable state changes.

Operations supplies the control mechanism; domain systems retain domain policy.

### 5. Behavioral edge tests
After Tracking HTTP is authoritative, validate:
- normal traffic;
- rate limiting;
- concurrent connections;
- oversized requests;
- upstream failure;
- restart/recovery;
- non-leaking logs.

## Completion rule

Operations is complete only when these items are implemented or explicitly blocked by an external dependency, tested, documented, and represented in the handoff. Real outbound production remains disabled until the final system-wide production gate passes.
