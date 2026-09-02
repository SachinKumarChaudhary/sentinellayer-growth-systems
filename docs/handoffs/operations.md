# Operations Handoff

**Status:** IN_PROGRESS  
**Owner:** operations  
**Protocol:** `docs/architecture/MULTI_AGENT_OPERATING_PROTOCOL.md`

## Current status

Operations CI/CD and runtime baseline are implemented. The production target is now explicitly self-hosted on an owner-controlled laptop. Remaining work is runtime validation, observability/recovery drills, and production-gate validation.

## Completed

- CI safety gate
- lint/type/unit/contract gates
- dependency audit
- Docker build gate
- non-root container assertion
- CI concurrency control
- runtime health/readiness probe
- Docker healthcheck
- tag-based immutable release workflow
- release manifest/artifact
- incident runbook
- operations machine-readable manifest
- repository secret scanning workflow
- self-hosted laptop runtime contract
- self-hosted Docker Compose worker baseline

## Operations-owned paths

- `.github/workflows/*`
- `scripts/ci-gate.sh`
- `src/sentinellayer_growth_engine/health.py`
- `tests/test_health.py`
- `Dockerfile`
- `docs/operations/*`
- `systems/operations.yaml`

## Dependencies

Operations depends on Platform for shared contracts and integration boundaries, and on domain systems for domain-owned health signals and safety policies.

## Remaining

1. Verify secret scanning passes in CI.
2. Validate the security workflow in CI.
3. Add migration validation once the repository's Supabase migration layout/CLI configuration is authoritative.
4. Add the self-hosted reverse-proxy/Tracking edge once Tracking's HTTP contract is merged.
5. Select and wire centralized/local metrics and logs for the laptop runtime.
6. Configure operational alert thresholds with domain owners.
7. Execute backup/restore, reboot, network-interruption, and rollback drills in staging.
8. Complete the production-readiness gate after Campaign, Tracking, Mail, and shared contracts are complete.

## Blockers

No current implementation blocker for the worker runtime. Tracking edge integration depends on Tracking PR #6; migration validation depends on the authoritative Supabase migration layout.

## Risks

- Domain systems may introduce shared contract changes; those changes must go through Platform.
- Operations must not invent domain thresholds.
- Real outbound sending remains disabled until explicit production approval.

## Next action

Validate CI/security, then implement the self-hosted HTTP edge against the merged Tracking contract. Do not modify shared domain contracts without Platform review.
