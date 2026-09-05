# SentinelLayer System Readiness Matrix

This matrix is the single operator-facing readiness view. A subsystem is considered implementation-complete when its deterministic code path, persistence boundary, contracts, and automated tests are present. Provider/infrastructure activation is tracked separately.

| System | Implementation | Automated validation | External activation gate |
|---|---|---|---|
| Platform / Contracts | Complete | CI + contract suite | None |
| Intelligence | Foundation complete | Unit/contract coverage present | Real data/pipeline validation |
| Campaign / Messaging | Complete | Unit + synthetic lifecycle | Campaign content/QA |
| Scheduler / Execution | Complete | Unit + integration/concurrency | Worker deployment |
| Mail / Deliverability | Complete | Unit + live DB concurrency | SMTP/provider + domain |
| Tracking | Complete | Unit + contract coverage | Public edge/load validation |
| Conversation | Complete | Unit + synthetic lifecycle | Real mailbox/provider |
| Sales | Complete | Unit + handoff tests | Human process/CRM integration |
| Analytics / Attribution | Foundation complete | Contract/foundation tests | Outcome/revenue data |
| Operations / Control Plane | Core complete | CI + live DB | Deployment/recovery evidence |
| Operator Interface | CLI foundation | Unit/CI | Dashboard/API expansion |
| Hermes / AI | Boundary defined | Contract/tool validation | Agent credentials/runtime |
| Deployment | Docker + native Python capable | Build/non-root/health gates | VPS deployment |
| Security | Fail-closed boundaries | CI/dependency/safety gates | Final access/RLS review |
| Real-provider E2E | Not activated | Synthetic E2E complete | SMTP + IMAP + DNS + test recipient |

## Dependency order

1. Platform/contracts
2. Intelligence
3. Campaign
4. Scheduler/execution
5. Mail
6. Tracking
7. Conversation
8. Sales
9. Analytics
10. Operations
11. Operator interface
12. Hermes integration
13. Real-provider activation

## Current decision

Do not enable broad outbound sending until the external activation gates are evidenced. The repository must remain safe by default.
