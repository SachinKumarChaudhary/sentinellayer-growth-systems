# Operations Runtime

Self-hosted runtime controls for the SentinelLayer laptop target.

## Scripts

- `scripts/selfhosted/deploy.sh`: validate configuration and start the Compose stack.
- `scripts/selfhosted/rollback.sh`: deploy an explicitly selected known-good release with real outbound email disabled.

## Safety

Production secrets are external to Git. Real outbound email is disabled unless the separate production gate is explicitly satisfied.

## Runtime

- Python services run as non-root.
- Nginx is the only public HTTP edge.
- Tracking is not published directly.
- Mail worker is not publicly exposed.
- Health/readiness checks must remain non-consequential.

## Operational principle

A container restart or host reboot must never be treated as permission to replay outbound work. Reconcile durable Mail state first.
