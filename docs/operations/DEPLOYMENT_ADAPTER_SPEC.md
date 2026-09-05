# Self-Hosted Deployment Adapter Specification

## Purpose

Provide one reproducible deployment path for the laptop target.

## Required sequence

1. Validate host prerequisites.
2. Validate environment and safety settings.
3. Select immutable application release.
4. Build or load the release image.
5. Render/validate Compose configuration.
6. Start/update services.
7. Wait for readiness.
8. Run synthetic smoke checks.
9. Record deployed version/commit.
10. Fail closed on any safety/readiness failure.

## Safety

- Never inject production secrets from Git.
- Never enable real email implicitly.
- Never treat a successful container start as sufficient readiness.
- Never replay outbound work during recovery without reconciliation.

## Rollback

Rollback selects a previously verified immutable release, reapplies configuration, waits for readiness, executes smoke tests, and verifies durable mail state before resuming outbound execution.
