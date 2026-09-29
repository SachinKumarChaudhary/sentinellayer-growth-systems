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

## Second implementation slice

- CRM read models implemented for Accounts Index, Account 360, deterministic account search, and unified timeline.
- CRM service boundary implemented with actor context and stable error codes.
- Live Supabase compatibility checks passed for the Accounts Index and Account 360 query shapes.
- CRM test suite now contains 12 passing tests.

## Migration tooling

Profile a CSV or JSON source without mutating Supabase:

```bash
PYTHONPATH=. python scripts/profile_crm_source.py \
  --source /path/to/source.csv \
  --name production-sheet \
  --output source_snapshot.json
```

The profiler records exact headers, row count, null rates, file SHA-256, sample row hashes and importer version.

The importer intentionally does not invent a production Sheet schema. The exact production Google Sheet headers remain a pre-migration gate.

## HTTP adapter

`src/sentinellayer_growth_engine/crm/http.py` implements the frozen CRM routes over `CRMService`.

Authentication is injected with an `actor_resolver`; the transport does not trust a client-supplied user ID as authorization. Production deployment therefore still requires the repository's real auth/session layer.

Implemented transport routes include `/v1/crm/accounts`, account 360, `/v1/crm/search`, `/v1/crm/tasks`, state transitions, activity creation, task creation and note creation.

## Third implementation slice

- Deterministic source profiler for CSV/JSON.
- File SHA-256 and row-hash snapshots.
- Legacy lead-status parser preserving raw evidence.
- Explicit row dispositions with quarantine for ambiguous status.
- Replay-safe crm.migration_rows staging function.
- Dry-run-by-default staging CLI with explicit `--apply`.
- CRM HTTP transport adapter with injected actor resolver.

Verification:
- CRM tests: 23 passed.
- Adjacent db/sales/conversation compatibility tests: 36 passed.
- Full-repository baseline remains 452 passed, 7 skipped, 3 unrelated intelligence/compliance failures.

## Development server

`scripts/run_crm_api.py` provides a localhost-only development server. It requires:
- `SL_ENVIRONMENT=development`
- `SL_DATABASE_URL`
- `SL_CRM_DEV_ACTOR_USER_ID`

The static actor mode is rejected outside development. Production deployment must provide the real authenticated-session resolver before CRM mutations are exposed.

## Operator UI slice

- Added `dashboard/crm.html` as the CRM operator surface.
- Uses the canonical SentinelLayer palette: `#000513`, `#141936`, `#4A54E8`, `#7183EE`, `#F2F3F5`, `#A4A8BA`, `#6F7394`, `#404566`.
- Core screens: Today, Accounts, Contacts, Tasks, Pipeline and Account 360 drawer.
- Same-origin development server route: `/crm`.
- Account state actions include optimistic version + idempotency headers.
- UI is responsive for narrow screens; production auth remains a separate gate.

Verification:
- 40 CRM/adjacent compatibility tests passing.
- `/crm` HTTP smoke test: 200, `text/html`, correct CRM title.
