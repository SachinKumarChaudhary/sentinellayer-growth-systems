# Self-Hosted Recovery Drills

## Required drills

### Application rollback
Deploy known-good release → introduce controlled failure → rollback → readiness → smoke → verify queue/send state.

### Host reboot
Stop services → reboot host → verify Docker startup → verify service restart → readiness → smoke → verify no duplicate sends.

### Network interruption
Disconnect external network → verify bounded failures and no unsafe retry storm → restore network → verify recovery/reconciliation.

### Database restore
Create/verify a backup → restore into isolated Supabase environment → run migrations/contract checks → run synthetic lifecycle tests.

## Evidence

Each drill records:
- date/time
- release/version
- operator
- fault injected
- expected behavior
- observed behavior
- pass/fail
- follow-up issue

A drill is not considered passed without recorded evidence.
