# Production Control Plane Specification

## Safety states

```
DISABLED → ARMED → ENABLED
    ↑        ↓         ↓
    └──── SAFE STOP ←──┘
```

### DISABLED
No real outbound execution is permitted.

### ARMED
Production configuration and dependencies may be validated, but real outbound execution remains blocked.

### ENABLED
Real outbound execution is permitted only when all production gates are green and explicit human approval exists.

### SAFE STOP

Immediately prevents new outbound execution. Existing durable state is preserved for reconciliation.

## Required controls

- global outbound kill switch
- production-send enable/disable gate
- maintenance mode
- campaign pause override
- mailbox pause override
- audit record for every control-state change

## Separation

Operations provides control mechanisms. Mail/Campaign remain owners of domain eligibility and strategy. Operations must not bypass domain suppression or eligibility policies.

## Activation rule

No control can move the environment to ENABLED unless:
- production environment is explicitly configured;
- required secrets are available through approved injection;
- health/readiness is green;
- CI/release gate is green;
- staging prerequisites are satisfied;
- human approval is recorded.

## Recovery

SAFE STOP is the default state after an unrecoverable runtime error, safety-gate failure, or operator-triggered emergency stop.
