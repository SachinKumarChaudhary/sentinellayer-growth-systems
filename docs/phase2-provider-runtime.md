# Phase 2 Provider Runtime — Termux / GitHub parity

**Status:** Runtime configuration and provider preflight added. Full adapter integration into the Phase 2 batch runner remains separate work.

## Current execution boundary

The Termux OpenCode runtime has Keenable SELECT and the QorpIQ public MCP connected. The data.gov.in Company Master Data key was validated with an HTTP 200 response and a one-record response from the approved resource.

The current Python batch runner (`scripts/run_phase2_entity_resolution.py`) still executes the existing TinyFish Search/Fetch and optional Groq extraction path. The new providers are not yet invoked by that runner. This change makes the same OpenCode runtime/provider connections available in GitHub Actions and adds a bounded preflight; it does not silently alter entity adjudication.

## GitHub Actions secrets

Add these repository or `staging-mail` environment secrets:

| Secret | Used for | Required by the preflight |
| --- | --- | --- |
| `GROQ_API_KEY` | OpenCode's Groq model (`groq/openai/gpt-oss-20b`) | Yes |
| `KEENABLE_API_KEY` | Keenable SELECT remote MCP `X-API-Key` header | Yes |
| `DATA_GOV_IN_API_KEY` | data.gov.in Company Master Data API | Yes |
| QorpIQ key | No key for the public read-only MCP | No |

Do not commit real keys. The root `opencode.json` uses OpenCode's `{env:NAME}` interpolation and contains no secret values.

Existing full Phase 2 execution additionally requires the database and TinyFish secrets used by the existing semantic canary workflow (`SL_DATABASE_URL` or `SUPABASE_DATABASE_URL`, and `SL_TINYFISH_API_KEY` or `TINYFISH_API_KEY`). Those are intentionally not required by the provider preflight.

## Run the provider preflight

1. Add the three required GitHub secrets above.
2. Open **Actions → Phase 2 Provider Runtime Smoke → Run workflow**.
3. Keep the Groq model smoke enabled for the first run.

The manual workflow:
- installs OpenCode CLI 2.0.18, matching the inspected Termux version;
- verifies Keenable SELECT and QorpIQ connect through OpenCode MCP;
- checks one data.gov.in record and QorpIQ service status;
- optionally runs one minimal Groq completion;
- processes zero leads, writes no database rows, sends no email, and does not call QorpIQ's paid REST API.

The Keenable step checks MCP connection only; it does not execute a search query or consume a deliberate search credit. Live research calls should be introduced as an explicitly budgeted pilot after credentials and connectivity pass.

## Provider role and evidence rules

- **TinyFish:** remains the primary external Phase 2 research path in the Python runner.
- **Keenable SELECT:** secondary targeted search for unresolved missions; returned search text is discovery material, not final evidence.
- **data.gov.in:** Indian company-master identity/status data. It is India-specific and does not establish website operation, ownership, functional control or ICP fit by itself.
- **QorpIQ public MCP:** Indian company/CIN/LLPIN/DIN/status lookup using its stored registry data. It is not a live MCA query for every request. The separate paid REST API is out of scope.
- **Groq/OpenCode:** performs bounded model/tool orchestration and optional extraction. It never owns the final entity decision.
- **Deterministic Phase 2 policy:** owns entity identity, relationship semantics, temporal/currentness handling and adjudication.

**Source-lineage constraint:** data.gov.in, MCA-derived records and QorpIQ can represent the same underlying registry filing/master-data lineage. Deduplicate correlated records; do not count them as independent corroboration.

## Next implementation step

After the runtime preflight passes, implement and test provider-neutral Python adapters for the bounded Indian-registry use case, then integrate them into candidate generation/research without changing the Phase 2 decision contract. Keep India registry lookups conditional on Indian legal-entity evidence; do not run them against unrelated US leads.
