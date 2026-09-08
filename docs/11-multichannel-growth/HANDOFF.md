# HANDOFF — Sentinel Layer Growth Systems

**Date:** 2026-09-08
**Purpose:** Give another ChatGPT/Codex session the exact context needed to continue implementation without re-deciding architecture or hallucinating missing details.

## Read these files first

1. `docs/11-multichannel-growth/DECISION_LOG.md`
2. `docs/11-multichannel-growth/CANONICAL_SYSTEM_DESIGN.md`
3. `docs/11-multichannel-growth/ENRICHMENT_AND_INTENT_PIPELINE.md`
4. `docs/11-multichannel-growth/OUTREACH_AND_OPERATOR_WORKFLOW.md`
5. `docs/11-multichannel-growth/TRACKING_CTA_ATTRIBUTION.md`
6. `docs/11-multichannel-growth/AI_AGENT_AND_TOOLING_CONTRACT.md`
7. `docs/11-multichannel-growth/SUPABASE_SCHEMA.md`
8. `docs/11-multichannel-growth/EXTERNAL_INTEGRATION_CONSTRAINTS.md`
9. Existing Decision Makers Playbook
10. Existing Buying Intent Classification v2.1 / Lead Classification Playbook
11. Existing Enrichment / Deep Enrichment and Free Oracles documents

The files in `docs/11-multichannel-growth/` are the canonical architecture/decision layer. Do not contradict them without an explicit new decision.

## Product direction

Build a company-centric, multi-channel growth system whose current objective is more meetings/sales.

Primary KPI right now: `meeting_booked`.

Channels cooperate; do not build a channel-vs-channel optimizer.

Company is the ICP/root object.

A company may participate in multiple campaigns and different decision makers may be targeted by different campaigns.

Decision-maker contact methods belong to the decision-maker record.

Generic company contacts are separate.

Email can execute automatically only after human/operator approval of a personalized sequence.

LinkedIn/Instagram/Reddit use Composio where the connected account actually exposes the required capability. Unsupported or consequential actions become operator tasks.

Hermes is the operating agent. Sentinel Layer remains the system of record.

Phone automation is future scope.

Social content is optional warming, not a prerequisite to DM. AI may recommend content based on buying intent.

## Enrichment model

There are 1,200 existing companies in Supabase. Start from these from scratch for the new canonical enrichment pipeline. Do not build the new system around the old 485-company enriched dataset.

Pipeline:

```
1200 companies
 -> company enrichment
 -> buying-intent research
 -> decision-maker planning
 -> decision-maker discovery
 -> public contact/social discovery
 -> email candidate verification
 -> evidence validation
 -> FIT + INTENT + priority
 -> campaign-ready
```

Research is intentionally small-batch/high-accuracy for AI-assisted enrichment: typically 1–3 companies at a time.

General-purpose chat AIs (ChatGPT/Gemini/Claude/Grok/DeepSeek) are being used as research assistants/operators for public-web enrichment. They should return structured evidence, not unsupported claims.

TinyFish Search/Fetch is the primary systematic web research resource and should be used aggressively within current limits, with caching and rate-aware scheduling. Do not use TinyFish Browser automation for this project.

Current verified public TinyFish limits documented in `EXTERNAL_INTEGRATION_CONSTRAINTS.md`:
- Search: 30 requests/minute, 500 requests/hour, free.
- Fetch: 150 URLs/minute, 1,000 URLs/day, free.
- Agent: 2 concurrent, metered.
- Browser: 5 concurrent, metered.

Apify is primarily for email finding/enrichment, not general scraping. Multiple Apify API keys are supported through a credential pool; keys stay in secret storage, Supabase stores references/health/cooldown/usage, and exhausted keys rotate out.

Free email/domain oracles should run before QEV/Email Hippo. Do not pay to verify every candidate.

Email candidate != verified email. Preserve source/provenance and verification state.

## Decision-maker logic

The uploaded Decision Makers Playbook is canonical.

It is conditional, not a simple static rank list.

Examples:
- CISO/security if available -> strong first target.
- No CISO -> CTO/VP Engineering often becomes security owner.
- Smaller companies -> Founder/CEO becomes more important.
- 150–500 employee companies -> CTO plus COO/CFOO/economic thread.
- Health/kids/age-gated -> consider Legal.
- IoT -> Product/IoT thread.
- Subscription/financial pain -> Finance/Payments.

Normally find at least two strong decision makers where evidence supports them.

Do not invent people or URLs. A correct not-found result is better than fabricated evidence.

## Buying-intent logic

Use the newer v2 model as canonical:
- `fit_score_v2`
- `intent_score_v2`
- `priority`

Legacy score/tier is historical only.

Separate:
- FIT = structural suitability
- INTENT = current/dated buying window
- BEHAVIOR = first-party engagement

Use immutable `intent_signals` with signal date, weight, half-life, evidence and confidence.

AI does not invent the deterministic FIT/INTENT/routing formula when the playbook already defines it.

Reddit/web dark-funnel signals can:
1. enrich a known company, or
2. discover a new candidate company.

A Reddit identity does not need to be resolved to be useful as a company-level signal.

## Outreach model

Hierarchy:

```
Monthly campaign
 -> campaign batch
 -> company enrollment
 -> decision-maker state
 -> AI-recommended sequence
 -> operator approval
 -> touchpoints
```

Initially use batches/lists. Later run monthly strategic campaigns.

Contact state is person-centric:
- not_contacted
- active
- awaiting_reply
- replied
- follow_up_due
- meeting
- closed
- suppressed

Channel activity is stored separately.

AI recommends the next channel/action; human/operator approves consequential actions.

If someone explicitly opts out:
- suppress the relevant contact/scope.
- A CISO saying not to contact them does NOT automatically suppress other decision makers.
- Company-wide do-not-contact suppresses the company.
- Cross-contact decisions require human review.

## Tracking / attribution

Do not force one channel to receive exclusive credit.

Persist the journey:

```
strategy
 -> content/message
 -> placement
 -> CTA
 -> touchpoint
 -> website event
 -> conversation
 -> meeting
```

Meeting is the current conversion objective.

Important behavioral evidence:
- conversations
- CTA clicks
- meeting-page visits

For public social content, do not invent person-level impression identity when the platform does not legitimately provide it.

A separate domain is not currently required. Primary branded domain can use a `/go/` path; opaque tokens remain internal attribution identifiers.

Avoid ugly opaque links in public social-profile/post copy where a branded destination is preferable.

## Canonical Supabase schema

The current live database already contains 1,200 rows in `public.companies`. This remains the company system of record.

New canonical namespaces/tables were added/applied for:
- `growth.decision_makers`
- `growth.decision_maker_contact_methods`
- `growth.company_contacts`
- `intelligence.enrichment_runs`
- `intelligence.evidence`
- `intelligence.intent_signals`
- `intelligence.company_scores`
- `intelligence.company_facts`
- `growth.campaigns`
- `growth.campaign_batches`
- `growth.campaign_company_enrollments`
- `growth.contact_campaign_states`
- `outreach.sequences`
- `outreach.sequence_approvals`
- `outreach.touchpoints`
- `outreach.execution_attempts`
- `ops.provider_credentials`
- `ops.provider_pools`
- `ops.provider_pool_members`
- `attribution.edges`

Existing conversation/tracking systems are to be extended, not duplicated.

## Current implementation

Important implemented code:
- `src/sentinellayer_growth_engine/enrichment_contracts.py`
- `src/sentinellayer_growth_engine/enrichment_repository.py`
- `src/sentinellayer_growth_engine/intelligence_scoring.py`
- `src/sentinellayer_growth_engine/cli.py`
- `tests/test_enrichment_contracts.py`
- `tests/test_intelligence_scoring.py`
- `schemas/enrichment-batch.schema.json`
- `supabase/migrations/20260908102500_multichannel_growth_foundation.sql`

The enrichment contract is deliberately limited to 1–3 companies per AI batch and forbids the research agent from claiming verification through labels like VERIFIED/INFERRED/NOT_FOUND. Current contract code includes `CompanyFacts`, decision makers, company contacts, intent signals and evidence. fileciteturn582file0

The operator CLI supports the small-batch workflow conceptually:
- `slctl enrichment export-next --limit 3`
- `slctl enrichment import --file <json>`

The export selects companies without a completed `intelligence.enrichment_runs` record.

## Conversation/Groq status

The earlier provider-conversation → queue → Groq E2E work is already functioning.

Verified database state has multiple completed analysis jobs with:
- `status = completed`
- `provider = groq`
- `model = openai/gpt-oss-20b`
- structured analysis present

A real interested inbound has also produced an open sales task.

The provider conversation smoke can automatically discover a fresh controlled reply from the staging mailbox by provider Message-ID, process it through `ConversationRuntime.handle_inbound()`, assert durable analysis enqueue, and verify duplicate idempotency. Its workflow is manual `workflow_dispatch`; do not add a permanent push trigger. fileciteturn587file0

## CI situation at handoff

One previous Groq verification workflow failed because it found zero pending jobs. That is expected for a queue-verification workflow when the queue was already drained; it was not a Groq API failure. Its logs showed:
- Groq authorization HTTP 200
- structured-output diagnostic HTTP 200
- worker processed 0 because queue was empty
- workflow intentionally failed on the empty-queue invariant.

Supabase concurrency integration has passed.

A later integration run on main is the active/final verification point; inspect the newest run against the actual latest `main` SHA before claiming CI is green.

Do not assume a run is testing the current commit. Always check:
1. workflow `head_sha`
2. checkout SHA
3. job conclusion
4. relevant logs

## Known coding issue to inspect before continuing

The newly added enrichment repository code should be tested against the actual current Python package and existing database conventions before expanding it.

Pay particular attention to:
- any mismatch between existing `public.companies` column names and CLI export SQL
- compatibility between the new UUID decision-maker model and existing `public.people`
- evidence linking after decision-maker IDs are created
- whether `CompanyFacts` is persisted by the repository (the table exists; the writer should store it)
- whether the GitHub migration runner will apply the new growth migration cleanly
- CI Ruff/MyPy/test results on the latest commit

Do not declare the enrichment feature complete merely because tables exist.

## What the next session should do

1. Read all canonical docs above.
2. Inspect the latest `main` commit and changed files.
3. Inspect the latest CI run and wait/poll until it reaches a terminal state. Use GitHub Actions job reruns where needed rather than asking the user to manually intervene.
4. Fix any CI failures caused by our changes.
5. Validate the live Supabase growth schema against the migration and confirm no destructive duplication occurred.
6. Finish the enrichment repository writer, including persistence of `intelligence.company_facts`.
7. Add repository tests for:
   - 1-company import
   - 3-company import
   - >3 rejection
   - duplicate company rejection
   - AI cannot claim verification
   - evidence dedupe
   - decision-maker/contact upsert
   - company-facts persistence
8. Add the actual decision-maker research/ranking implementation from the playbook.
9. Add the actual intent-signal normalization/scoring adapter from the playbook.
10. Wire campaign enrollment/recommendation state only after the data layer is stable.
11. Extend CTA/tracking/conversation integration without duplicating existing foundations.
12. Add CI contract tests for future changes so stale/wrong pulls cannot contaminate E2E runs.
13. Run the real E2E tests and inspect final database rows before declaring completion.

## Critical operating rules

- Do not ask the user to supply message IDs that can be discovered automatically.
- Do not ask the user to dispatch a workflow if the GitHub tool can dispatch/rerun it.
- Do not use TinyFish Browser automation.
- Use TinyFish Search/Fetch only for web research.
- Do not create real outbound emails for controlled E2E tests.
- Do not treat an LLM claim as verification.
- Do not invent Composio capabilities; inspect the actual toolkit/account capabilities.
- Do not invent missing data; record unknown/not-found safely.
- Do not change deterministic business rules merely because an LLM suggests another score.
- Do not run a huge unbounded enrichment job. The intended research operation is controlled and rate-limited.
- Do not modify the existing primary email/domain setup solely for CTA tracking.
- Do not add automatic calling now.
- Human approval remains required for consequential outreach.

## Full-context retrieval strategy

If this handoff is the only thing visible in the new session, use the GitHub connector to fetch the listed canonical files directly from:

`https://github.com/SachinKumarChaudhary/sentinellayer-growth-systems`

Then inspect current source and Supabase state. This document describes decisions, but **the live repository/database is the authority for what is actually implemented**.

When there is a discrepancy:
- current code/database tells you current state
- this handoff + canonical docs tell you intended design
- do not silently reconcile; document the discrepancy and fix it deliberately

