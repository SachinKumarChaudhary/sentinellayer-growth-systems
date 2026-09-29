# CRM MVP Implementation

Status: implementation started on 2026-09-30.

## Implemented

- crm.account_state operator state overlay.
- crm.contact_state contact state overlay.
- crm.notes for account/contact notes.
- crm.state_history append-only state history.
- crm.audit_events append-only mutation audit.
- crm.migration_rows row-level migration/reconciliation staging.
- Canonical compatibility columns on sales.tasks.
- Canonical compatibility columns on conversation.threads and conversation.replies.
- Optional CRM task contact reference while the legacy sales.tasks.person_id field is retained.
## Code

src/sentinellayer_growth_engine/crm/state.py
- deterministic account/contact state transition rules.
- explicit unsuppress authorization requirement.

src/sentinellayer_growth_engine/crm/repository.py
- transactional state initialization and transitions.
- optimistic version checking.
- idempotent audit replay.
- note creation.
- manual activity creation through outreach.touchpoints.
- canonical CRM task creation.
- deterministic task queue ordering.

 tests/test_crm_state.py
- positive account/contact paths.
- invalid transitions.
- same-state rejection.
- suppression/unsuppress guard.
## Migrations

- 20260930010000_crm_mvp_foundation.sql
- 20260930011000_crm_security_hardening.sql

Both are applied to the connected Supabase project.
## Compatibility strategy

The current production system still uses legacy text identifiers in conversation/tasks. The CRM migration adds canonical FK columns rather than rewriting those identifiers in place.

Current observed production smoke task contains:
- account_id = staging-provider-smoke
- person_id = 877

Because these do not resolve to canonical CRM identities, the migration intentionally leaves the new canonical columns null. No record was silently reinterpreted.
## Verification

CRM-targeted tests pass.

The full repository suite currently reports:
- 452 passed
- 7 skipped
- 3 unrelated failures in existing intelligence/compliance tests

A missing repository-root Python path also caused one initial collection error; rerunning with PYTHONPATH=. produced the result above.
## Next implementation slice

1. CRM read models / Account 360 / timeline queries.
2. API/service boundary with authenticated actor context.
3. migration importer and source snapshot generation.
4. permission/RLS policy definitions after actor-scope mapping is frozen.
5. operator UI.
6. G01–G20 integration and UAT.
