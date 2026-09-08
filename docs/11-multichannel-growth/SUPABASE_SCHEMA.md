# Sentinel Layer — Canonical Supabase Schema for Multi-Channel Growth

**Status:** Canonical design baseline  
**Date:** 2026-09-08  
**Purpose:** Database contract for company-centric enrichment, multi-channel outreach, intent, tracking and meetings.

## 1. Design principles

- Company is the ICP/root object.
- Decision makers are people attached to companies; their outreach identities live with the decision-maker record.
- Generic organization contacts are separate.
- A company can belong to multiple campaigns.
- Contact progression is person-centric; channel actions are touchpoints.
- Conversations are durable and separate from delivery mechanics.
- Intent is represented as immutable evidence/signals plus derived current scores.
- Tracking events are immutable observations.
- Recommendations are derived; they are not the system of record.
- Meetings are business outcomes.
- Secrets are never stored as plaintext in ordinary application tables.

## 2. Schemas/namespaces

Use PostgreSQL schemas to separate domains:

- `growth` — companies, people, decision makers, campaigns, outreach state.
- `intelligence` — enrichment runs, evidence, intent signals, derived intelligence.
- `outreach` — touchpoints, sequences, approvals, provider executions.
- `conversation` — conversations/messages/analysis jobs/analysis results.
- `tracking` — first-party events, CTA links, placements, sessions.
- `attribution` — lineage edges and meeting attribution context.
- `ops` — provider accounts, credential references, rate-limit state, job leases.

Keep existing schema names where the current production system already owns a concept; introduce these namespaces incrementally rather than duplicating existing tables.

## 3. Core tables

### public.companies (existing system of record)

The repository already has 1,200 company rows in `public.companies`. This table remains the canonical company root.

The new growth/intelligence tables reference `public.companies(id)` rather than creating a duplicate company table.

Do not store decision makers as a delimited text field here.

### Existing public.people

The repository already has `public.people`, but the new canonical enrichment model uses `growth.decision_makers` because your current requirement is company -> decision makers, with their outreach identities attached to them. Existing `public.people` remains legacy/compatibility data until the outreach execution layer is migrated.

### growth.decision_makers

Canonical decision-maker records for the new enrichment pipeline. Each row belongs to a company and contains role/ranking/research state.

### growth.decision_maker_contact_methods

All individual outreach identities belonging to a decision maker.

```
growth.person_contact_methods
  contact_method_id
  person_id
  channel
  value
  normalized_value
  source
  source_url
  verification_status
  verification_provider
  confidence
  first_seen_at
  last_verified_at
```

This keeps all individual contact surfaces attached to the decision-maker.

### growth.company_contacts

Generic organization routes.

Examples:
- info@
- hello@
- support@
- sales@
- press@
- main company phone
- contact form

Fields:
- company_contact_id
- company_id
- channel
- value
- source_url
- verification_status
- confidence
- first_seen_at
- last_verified_at

## 4. Intelligence tables

### intelligence.enrichment_runs

One run per enrichment operation.

Fields:
- enrichment_run_id
- company_id
- run_type
- agent/provider
- started_at
- completed_at
- status
- error_code
- cost_estimate
- tool_usage JSONB

### intelligence.evidence

Immutable evidence record.

Fields:
- evidence_id
- company_id nullable
- person_id nullable
- claim_type
- claim_json JSONB
- source_url
- source_type
- observed_at
- event_date nullable
- agent/provider
- confidence
- evidence_hash

Unique/dedup key should prevent repeated identical evidence.

### intelligence.intent_signals

Immutable normalized buying-intent signals.

Fields:
- intent_signal_id
- company_id
- signal_type
- signal_date
- detected_at
- weight
- half_life_days
- evidence_id
- confidence
- status
- expires_at nullable

Do not overwrite old signals. New research creates new signals.

### intelligence.company_scores

Derived current state.

Fields:
- company_id PK/FK
- fit_score
- fit_raw
- intent_score
- behavior_override
- negative_flags JSONB
- modifiers JSONB
- priority
- scored_at
- scoring_version

Scores can be recomputed from immutable evidence.

## 5. Campaign tables

### growth.campaigns

Strategic monthly campaign container for the new growth system. Existing `public.campaigns` remains for compatibility until the campaign execution layer is migrated.

Fields:
- campaign_id
- name
- campaign_month
- strategy_version_id
- offer_version_id
- status
- created_at / updated_at

### growth.campaign_batches

Operational list/batch.

Fields:
- batch_id
- campaign_id
- name
- source
- imported_at
- status

### growth.campaign_enrollments

Company-level campaign membership.

Fields:
- enrollment_id
- campaign_id
- batch_id
- company_id
- status
- priority_snapshot
- enrolled_at
- exited_at

Unique: `campaign_id, company_id`.

### growth.contact_campaign_states

Contact state within a campaign.

Fields:
- state_id
- enrollment_id
- company_person_id
- state
- next_action_at
- last_contacted_at
- last_replied_at
- suppression_scope
- notes
- updated_at

This is where `not_contacted / active / awaiting_reply / replied / follow_up_due / meeting / closed / suppressed` lives.

## 6. Outreach tables

### outreach.sequences

AI-generated sequence proposal.

Fields:
- sequence_id
- enrollment_id
- company_person_id
- recommendation_id
- sequence_json
- model/agent
- generated_at
- status

### outreach.sequence_approvals

Fields:
- approval_id
- sequence_id
- approved_by
- approved_at
- decision
- edited boolean
- notes

### outreach.touchpoints

The canonical record of every concrete interaction/action.

Fields:
- touchpoint_id
- enrollment_id
- company_person_id nullable
- channel
- touchpoint_type
- sequence_id
- cta_version_id nullable
- placement_id nullable
- parent_touchpoint_id nullable
- status
- scheduled_at
- executed_at
- provider
- provider_reference
- idempotency_key UNIQUE
- metadata JSONB

Examples:
- email_send
- linkedin_dm
- instagram_dm
- reddit_dm
- social_post
- social_comment
- profile_cta
- call_attempt (future)

### outreach.execution_attempts

Provider attempt log.

Fields:
- execution_attempt_id
- touchpoint_id
- attempt_number
- provider
- result
- provider_error_code
- started_at
- finished_at
- metadata JSONB

Do not overwrite attempts.

## 7. Conversation tables

Reuse the existing `conversation` foundation and generalize it to channel-neutral conversations.

### conversation.conversations
- conversation_id
- company_id
- primary_person_id nullable
- status
- started_at
- last_activity_at

### conversation.messages
- message_id
- conversation_id
- touchpoint_id nullable
- channel
- direction
- external_message_id
- body/reference
- sent_at/received_at
- source
- idempotency_key

### conversation.participants
- conversation_id
- person_id / external_identity
- role

### conversation.analysis_jobs
Retain existing queue semantics.

### conversation.analyses
Persist structured LLM results with provider/model/version metadata.

A cross-channel conversation may contain email, LinkedIn, Instagram and Reddit messages. Phone remains a future transcript-ingestion path.

## 8. Tracking tables

### tracking.ctas

Versioned CTA definitions.

### tracking.placements

Where the CTA appears:
- linkedin_profile
- linkedin_post
- instagram_profile
- instagram_post
- reddit_post
- email
- website

### tracking.opaque_links

Fields:
- token_hash
- token_prefix
- cta_id
- placement_id
- touchpoint_id nullable
- campaign_id
- company_id nullable
- person_id nullable
- destination
- expires_at
- revoked_at

Never store raw recipient identity in the public token.

### tracking.events

Immutable event stream.

Fields:
- event_id
- source_event_id
- event_type
- company_id nullable
- person_id nullable
- campaign_id nullable
- touchpoint_id nullable
- cta_id nullable
- placement_id nullable
- session_id nullable
- occurred_at
- source
- automation_classification
- confidence
- payload JSONB
- ingest_key UNIQUE

## 9. Attribution tables

### attribution.edges

Stores lineage between canonical objects.

Fields:
- edge_id
- from_type / from_id
- to_type / to_id
- relationship
- occurred_at
- evidence_event_id nullable

### attribution.meeting_attribution

Stores the meeting's canonical lineage snapshot.

Fields:
- meeting_id
- company_id
- person_id
- campaign_id nullable
- primary_touchpoint_id nullable
- first_touch_id nullable
- last_touch_id nullable
- journey_edge_ids JSONB
- booked_at
- source

The canonical truth is the journey; attribution-model percentages are derived reporting.

## 10. Operations/provider tables

### ops.channel_accounts

Connected execution accounts.

Fields:
- channel_account_id
- provider
- channel
- external_account_id
- owner_identity
- status
- capabilities JSONB
- connected_at
- last_checked_at

### ops.integration_credentials

Metadata only; never raw secret material.

Fields:
- credential_ref_id
- provider
- purpose
- secret_manager_ref
- status
- last_used_at
- last_error_at
- rate_limit_state JSONB
- priority
- created_at

Actual API keys belong in the deployment secret manager.

### ops.provider_pools

Provider key/account pool.

Fields:
- pool_id
- provider
- pool_name
- selection_policy
- enabled

### ops.provider_pool_members

Fields:
- pool_member_id
- pool_id
- credential_ref_id
- ordinal
- enabled
- cooldown_until
- consecutive_failures
- usage_snapshot JSONB
- last_selected_at

For Apify, multiple API keys can be rotated through this pool. The database records references and state; plaintext keys are not stored in Supabase application tables.

## 11. Constraints and indexes

Important indexes:
- companies.canonical_domain
- company_people.company_id
- decision_maker_contacts.company_person_id
- intent_signals.company_id + signal_date
- campaign_enrollments.campaign_id + company_id
- contact_campaign_states.enrollment_id + company_person_id
- touchpoints.enrollment_id + company_person_id + executed_at
- messages.conversation_id + received_at
- events.company_id + occurred_at
- events.person_id + occurred_at
- events.ingest_key UNIQUE
- opaque_links.token_hash UNIQUE

Use foreign keys and explicit uniqueness constraints for idempotency.

## 12. RLS/security

Keep operational tables in non-public schemas where possible.

If any table is exposed through Supabase Data API:
- enable RLS
- grant only required roles
- use explicit authorization predicates
- never expose service-role credentials

Do not expose raw provider credentials, private research artifacts, or internal attribution data to anonymous clients.

## 13. Migration strategy

The first foundation has now been applied to Supabase and committed as `20260908102500_multichannel_growth_foundation.sql`.

The existing `public.companies` table remains the source of truth for the 1,200 companies. Existing `public.people`, `public.campaigns`, conversation and tracking tables remain compatibility foundations. New growth/intelligence/outreach/ops tables are introduced incrementally.

Do not remove legacy fields until CI and live replay prove equivalence.

The first migration set should create:
- growth.companies
- growth.people
- growth.company_people
- growth.person_contact_methods
- growth.company_contacts
- intelligence.enrichment_runs
- intelligence.evidence
- intelligence.intent_signals
- intelligence.company_scores
- campaign relationship tables
- outreach.touchpoints/approvals
- ops provider-pool metadata

Conversation and tracking foundations already exist and should be extended rather than duplicated.
