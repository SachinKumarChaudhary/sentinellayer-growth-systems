# Operations Incident Runbook

## Golden rule
Contain first. Investigate second. Restore safely third. Do not trade safety for throughput.

## Severity

### Critical
Examples: uncontrolled duplicate-send risk, global safety failure, production database integrity risk, production system unavailable.
Action: activate containment/kill switch as appropriate and notify the owner immediately.

### High
Examples: sustained provider failures, abnormal bounce/complaint pattern, queue backlog, repeated worker crashes.
Action: pause affected scope, investigate, and restore only after health criteria pass.

### Medium
Examples: elevated latency, degraded non-critical dependency, approaching capacity.
Action: create operational task and monitor.

### Low
Informational or maintenance conditions.

## Global outbound incident

```text
Detect
 -> disable production-send gate or global outbound execution
 -> preserve logs/events
 -> identify last known good release
 -> inspect queue and send state
 -> verify no duplicate/unsafe retry path
 -> patch or rollback
 -> run staging/smoke validation
 -> restore gradually
 -> document incident
```

Never clear queued sends blindly. Reconcile durable state first.

## Mailbox/provider incident

```text
Provider failure/health anomaly
 -> mailbox pause if required
 -> record provider event
 -> determine accepted/failed/ambiguous scope
 -> do NOT blindly resend ambiguous messages
 -> reconcile
 -> verify provider health
 -> resume with controlled volume
```

Mail-specific thresholds remain owned by the Mail system; Operations owns alerting, containment controls, deployment and incident coordination.

## Database incident

```text
Detect
 -> stop risky writers where required
 -> preserve evidence
 -> determine migration/application version
 -> restore into isolated environment when appropriate
 -> validate integrity
 -> apply approved recovery
 -> run integration/concurrency checks
 -> resume gradually
```

Never rewrite an applied production migration to repair history.

## Deployment incident

```text
Deployment
 -> readiness failure or regression
 -> stop promotion
 -> inspect release/commit
 -> rollback to known-good artifact when safer
 -> verify health
 -> preserve failed artifact/version information
 -> create corrective change
```

## Secret exposure

```text
Suspected credential exposure
 -> revoke/rotate credential immediately
 -> prevent further use
 -> inspect repository/logs for propagation
 -> redeploy with rotated secret
 -> audit access
 -> document root cause
```

Never commit the replacement secret to Git.

## Recovery verification

A recovery is not complete until:
- service is healthy
- safety gates are active
- queue state is coherent
- no duplicate-send risk remains
- monitoring is receiving expected signals
- the relevant synthetic/smoke test passes
- incident notes record what happened and what changed
