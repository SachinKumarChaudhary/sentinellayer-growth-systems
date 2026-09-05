# Operations Execution Status

## Scope
This file records repository-verified Operations work and remaining production-gate dependencies.

## Implemented on Operations workstream
- CI safety and environment checks
- dependency audit
- lint/type/unit/contract gates
- Docker build and non-root validation
- runtime health/readiness
- immutable release workflow baseline
- self-hosted laptop runtime design
- self-hosted edge/rate-limit policy
- static edge/Compose validation

## Remaining
1. Centralized metrics/alerts implementation
2. Self-hosted deployment adapter implementation
3. Rollback/restore drill harness and evidence capture
4. Production control-plane state/controls
5. Behavioral tracking edge/load tests after authoritative Tracking HTTP merge
6. Verify CI evidence before closing CI-related issues

## Cross-system dependencies
- Platform owns shared contract/schema changes and cross-system contract tests.
- Campaign, Mail, and Tracking own their domain implementations.
- Real-provider staging and production mail readiness remain Mail-owned gates.

## Safety
Real outbound email must remain disabled until the complete production-readiness gate is satisfied and explicit human approval is recorded.
