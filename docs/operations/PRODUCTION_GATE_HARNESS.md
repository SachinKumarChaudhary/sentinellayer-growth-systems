# Production Gate Harness

This repository cannot execute real-host or real-provider drills in GitHub Actions because those require external staging credentials/infrastructure. This harness makes every such dependency explicit and fail-closed.

## Automated repository gate

The automated CI gate must prove:
- safety gate rejects production/real-email configuration;
- all unit/contract tests pass;
- self-hosted Nginx and Compose configuration validate;
- Docker image is non-root;
- canonical schema/version tests pass.

## External staging gates

The following require an isolated staging environment and must never be silently substituted with unit tests:
- authenticated Operations control-state mutation/audit;
- Mail pre-send control-state enforcement;
- provider SMTP smoke;
- DNS/mailbox readiness;
- Nginx behavioral rate/load tests;
- reboot/network/restore drills;
- final Campaign -> Mail -> Tracking -> Conversation lifecycle.

## Production activation rule

Real outbound mail remains disabled until all external gates are evidenced and an explicit human approval records the production activation decision.

## Evidence format

Each staging gate records:
- commit/release;
- environment;
- date/time;
- operator;
- test;
- expected result;
- observed result;
- pass/fail;
- remediation issue when failed.
