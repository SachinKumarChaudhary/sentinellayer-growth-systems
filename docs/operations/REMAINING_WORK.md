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
- fail-closed production gate harness and automated tests

## Remaining production-only gates

These cannot be honestly marked complete by GitHub CI alone because they require an isolated runtime/database/provider environment:

1. Authenticated Operations control-state mutation/audit exercise.
2. Mail pre-send enforcement of the Operations control state.
3. Local structured metrics/alerts connected to runtime signals.
4. Behavioral self-hosted Tracking edge/load test.
5. Deployment/readiness/rollback/reboot/network/restore drills.
6. Campaign → Mail → Tracking → Conversation synthetic E2E.
7. Controlled real-provider SMTP smoke test, DNS and mailbox readiness.
8. Final production activation review.

## Completion rule

Operations is complete only when the repository gates are green and the production-only gates above have recorded evidence. Real outbound email remains disabled until that evidence exists and explicit human approval is recorded.

## Authority

Platform owns shared contracts. Campaign, Mail, Tracking, and Conversation own domain behavior. Operations owns deployment, telemetry, safety controls, networking, recovery, and CI/CD.
