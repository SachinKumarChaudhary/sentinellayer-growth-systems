# Operations Implementation Plan

## Repository state verified

No existing Prometheus/metrics implementation, deployment command, rollback script, or production control-plane implementation was found on the default branch.

## Implementation order

1. Observability primitives and structured operational event format.
2. Self-hosted deployment/rollback scripts around Compose.
3. Durable production safety-control state and audit interface.
4. Recovery/drill scripts and evidence capture.
5. Behavioral edge tests after Tracking HTTP becomes authoritative.

## Constraints

- Operations may not invent domain semantics.
- Mail/Campaign/Tracking retain domain policy ownership.
- Platform owns shared contracts and cross-system schemas.
- Real outbound mail remains disabled until the system-wide production gate.
- Production configuration must not be stored in Git.

## Verification

Every implementation must have automated tests where deterministic, and staging-only drills where real infrastructure is required. CI is the authoritative repository gate.
