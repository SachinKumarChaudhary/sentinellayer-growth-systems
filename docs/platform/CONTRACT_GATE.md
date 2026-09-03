# Platform Contract Gate

The contract gate is intentionally deterministic and side-effect free.

## Required checks

1. Every supported shared schema version is explicitly registered.
2. Producers/consumers reject versions outside that registry.
3. Campaign output validates as RenderedSendTreatment.
4. Mail context preserves producer identity.
5. Provider outcome preserves send/correlation identity.
6. Tracking events preserve attribution identity.
7. No public client-controlled idempotency value participates in tracking replay identity.
8. Future Intelligence/Sales stages are represented by contracts/fixtures only until their implementations exist.

The gate does not send mail, contact external providers, or require future systems.

## Merge rule

A shared-contract change is not considered compatible until the corresponding contract tests and synthetic lifecycle gate pass in CI.
