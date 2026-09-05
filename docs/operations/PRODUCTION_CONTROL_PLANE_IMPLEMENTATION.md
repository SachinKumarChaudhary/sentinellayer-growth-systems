# Production Control Plane Implementation

## Durable state

Operational control state is stored in `operations.control_state`. Changes are audited in `operations.control_audit`.

## Safety states

- `DISABLED`: no real outbound execution.
- `ARMED`: dependencies/configuration may be validated; real outbound execution remains blocked.
- `ENABLED`: production outbound execution may proceed only after all production gates and explicit approval.
- `SAFE_STOP`: immediate safety containment; no new outbound work.

## Default safety posture

New environments start in `DISABLED` and maintenance mode. The migration creates no permissive RLS policies.

## Ownership

Operations owns the mechanism and audit trail. Mail and Campaign remain owners of domain eligibility, suppression, and strategy decisions.

## Required integration

The Mail execution boundary must consult the production control state before any real external send. A control-state failure must fail closed.

The control plane does not enqueue, send, retry, or suppress messages itself.

## Administrative boundary

Administrative mutations must occur only through an authenticated server-side path with least privilege. Every mutation records actor, action, previous state, new state, and reason.

## Production status

This migration provides the durable control-state foundation. An authenticated administrative API/control surface and end-to-end enforcement test remain required before ENABLED can be used in production.
