-- Canonical multi-channel growth foundation.
-- Applied/verified against the staging Supabase project on 2026-09-08.
-- The existing public.companies table remains the company system of record.

create schema if not exists growth;
create schema if not exists intelligence;
create schema if not exists outreach;
create schema if not exists ops;
create schema if not exists attribution;

create table if not exists growth.decision_makers (
  decision_maker_id uuid primary key default gen_random_uuid(),
  company_id bigint not null references public.companies(id) on delete cascade,
  full_name text not null,
  title text,
  role_family text,
  role_priority integer check (role_priority >= 1),
  rationale text,
  status text not null default 'candidate'
    check (status in ('candidate','validated','active','inactive','not_found')),
  research_status text not null default 'pending'
    check (research_status in ('pending','in_progress','complete','needs_review')),
  confidence numeric(5,4) check (confidence between 0 and 1),
  first_seen_at timestamptz not null default now(),
  last_verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists decision_makers_company_idx
  on growth.decision_makers(company_id);

create unique index if not exists decision_makers_company_name_title_uq
  on growth.decision_makers(company_id, lower(full_name), lower(coalesce(title,'')));

create table if not exists growth.decision_maker_contact_methods (
  contact_method_id uuid primary key default gen_random_uuid(),
  decision_maker_id uuid not null references growth.decision_makers(decision_maker_id) on delete cascade,
  channel text not null check (channel in ('email','phone','linkedin','instagram','reddit','x','other')),
  value text not null,
  normalized_value text not null,
  source text,
  source_url text,
  verification_status text not null default 'unknown'
    check (verification_status in ('unknown','candidate','verified','invalid','stale')),
  verification_provider text,
  confidence numeric(5,4) check (confidence between 0 and 1),
  first_seen_at timestamptz not null default now(),
  last_verified_at timestamptz,
  created_at timestamptz not null default now(),
  unique(decision_maker_id, channel, normalized_value)
);

create index if not exists dm_contacts_lookup_idx
  on growth.decision_maker_contact_methods(channel, normalized_value);

create table if not exists growth.company_contacts (
  company_contact_id uuid primary key default gen_random_uuid(),
  company_id bigint not null references public.companies(id) on delete cascade,
  channel text not null check (channel in ('email','phone','contact_form','other')),
  value text not null,
  normalized_value text not null,
  label text,
  source text,
  source_url text,
  verification_status text not null default 'unknown'
    check (verification_status in ('unknown','candidate','verified','invalid','stale')),
  confidence numeric(5,4) check (confidence between 0 and 1),
  first_seen_at timestamptz not null default now(),
  last_verified_at timestamptz,
  created_at timestamptz not null default now(),
  unique(company_id, channel, normalized_value)
);

create index if not exists company_contacts_company_idx
  on growth.company_contacts(company_id);

create table if not exists intelligence.enrichment_runs (
  enrichment_run_id uuid primary key default gen_random_uuid(),
  company_id bigint references public.companies(id) on delete cascade,
  run_type text not null,
  provider text,
  model_or_agent text,
  status text not null default 'queued'
    check (status in ('queued','running','completed','failed','partial')),
  started_at timestamptz,
  completed_at timestamptz,
  tool_usage jsonb not null default '{}'::jsonb,
  error_code text,
  created_at timestamptz not null default now()
);

create index if not exists enrichment_runs_company_idx
  on intelligence.enrichment_runs(company_id, created_at desc);

create table if not exists intelligence.evidence (
  evidence_id uuid primary key default gen_random_uuid(),
  enrichment_run_id uuid references intelligence.enrichment_runs(enrichment_run_id) on delete set null,
  company_id bigint references public.companies(id) on delete cascade,
  decision_maker_id uuid references growth.decision_makers(decision_maker_id) on delete cascade,
  claim_type text not null,
  claim jsonb not null,
  source_url text,
  source_type text,
  observed_at timestamptz not null default now(),
  event_date date,
  confidence numeric(5,4) check (confidence between 0 and 1),
  evidence_hash text,
  created_at timestamptz not null default now(),
  check (company_id is not null or decision_maker_id is not null)
);

create unique index if not exists evidence_hash_uq
  on intelligence.evidence(evidence_hash)
  where evidence_hash is not null;

create index if not exists evidence_company_idx
  on intelligence.evidence(company_id, observed_at desc);

create index if not exists evidence_dm_idx
  on intelligence.evidence(decision_maker_id, observed_at desc);

create table if not exists intelligence.intent_signals (
  intent_signal_id uuid primary key default gen_random_uuid(),
  company_id bigint not null references public.companies(id) on delete cascade,
  signal_type text not null,
  signal_date date not null,
  detected_at timestamptz not null default now(),
  weight numeric(8,4) not null,
  half_life_days integer not null check (half_life_days > 0),
  evidence_id uuid references intelligence.evidence(evidence_id) on delete set null,
  confidence numeric(5,4) check (confidence between 0 and 1),
  status text not null default 'active'
    check (status in ('active','expired','retracted')),
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists intent_signals_company_date_idx
  on intelligence.intent_signals(company_id, signal_date desc);

create index if not exists intent_signals_active_idx
  on intelligence.intent_signals(status, signal_date desc);

create table if not exists intelligence.company_scores (
  company_id bigint primary key references public.companies(id) on delete cascade,
  fit_score numeric(5,2) not null default 0 check (fit_score between 0 and 10),
  intent_score numeric(5,2) not null default 0 check (intent_score between 0 and 10),
  behavior_override boolean not null default false,
  negative_flags jsonb not null default '[]'::jsonb,
  modifiers jsonb not null default '[]'::jsonb,
  priority text not null default 'P4'
    check (priority in ('P1','P2','P3','P4')),
  scoring_version text not null default 'v2.1',
  scored_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists growth.campaigns (
  campaign_id uuid primary key default gen_random_uuid(),
  name text not null,
  campaign_month date,
  strategy_version_id uuid,
  offer_version_id uuid,
  status text not null default 'draft'
    check (status in ('draft','review','active','paused','completed','cancelled')),
  audience_definition jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists growth.campaign_batches (
  batch_id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references growth.campaigns(campaign_id) on delete cascade,
  name text not null,
  source text,
  status text not null default 'draft'
    check (status in ('draft','ready','active','completed','cancelled')),
  imported_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists campaign_batches_campaign_idx
  on growth.campaign_batches(campaign_id);

create table if not exists growth.campaign_company_enrollments (
  enrollment_id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references growth.campaigns(campaign_id) on delete cascade,
  batch_id uuid references growth.campaign_batches(batch_id) on delete set null,
  company_id bigint not null references public.companies(id) on delete cascade,
  priority_snapshot text,
  status text not null default 'pending'
    check (status in ('pending','active','paused','completed','suppressed','cancelled')),
  enrolled_at timestamptz not null default now(),
  exited_at timestamptz,
  exit_reason text,
  metadata jsonb not null default '{}'::jsonb,
  unique(campaign_id, company_id)
);

create index if not exists campaign_company_due_idx
  on growth.campaign_company_enrollments(status, enrolled_at);

create table if not exists growth.contact_campaign_states (
  contact_campaign_state_id uuid primary key default gen_random_uuid(),
  enrollment_id uuid not null references growth.campaign_company_enrollments(enrollment_id) on delete cascade,
  decision_maker_id uuid not null references growth.decision_makers(decision_maker_id) on delete cascade,
  state text not null default 'not_contacted'
    check (state in ('not_contacted','active','awaiting_reply','replied','follow_up_due','meeting','closed','suppressed')),
  next_action_at timestamptz,
  last_contacted_at timestamptz,
  last_replied_at timestamptz,
  suppression_scope text check (suppression_scope in ('channel','campaign','global')),
  notes text,
  updated_at timestamptz not null default now(),
  unique(enrollment_id, decision_maker_id)
);

create table if not exists outreach.sequences (
  sequence_id uuid primary key default gen_random_uuid(),
  enrollment_id uuid not null references growth.campaign_company_enrollments(enrollment_id) on delete cascade,
  decision_maker_id uuid references growth.decision_makers(decision_maker_id) on delete set null,
  generated_by text,
  generated_at timestamptz not null default now(),
  sequence_json jsonb not null,
  status text not null default 'draft'
    check (status in ('draft','approved','active','paused','completed','rejected','cancelled')),
  confidence numeric(5,4) check (confidence between 0 and 1)
);

create index if not exists outreach_sequences_status_idx
  on outreach.sequences(status, generated_at desc);

create table if not exists outreach.sequence_approvals (
  approval_id uuid primary key default gen_random_uuid(),
  sequence_id uuid not null references outreach.sequences(sequence_id) on delete cascade,
  decision text not null check (decision in ('approved','rejected','edited')),
  approved_by text not null,
  approved_at timestamptz not null default now(),
  notes text
);

create table if not exists outreach.touchpoints (
  touchpoint_id uuid primary key default gen_random_uuid(),
  enrollment_id uuid references growth.campaign_company_enrollments(enrollment_id) on delete set null,
  decision_maker_id uuid references growth.decision_makers(decision_maker_id) on delete set null,
  company_id bigint references public.companies(id) on delete cascade,
  sequence_id uuid references outreach.sequences(sequence_id) on delete set null,
  channel text not null check (channel in ('email','linkedin','instagram','reddit','social_content','website','phone')),
  touchpoint_type text not null,
  cta_id uuid,
  placement_id uuid,
  parent_touchpoint_id uuid references outreach.touchpoints(touchpoint_id) on delete set null,
  status text not null default 'planned'
    check (status in ('planned','approved','queued','sent','delivered','failed','cancelled','completed')),
  scheduled_at timestamptz,
  executed_at timestamptz,
  provider text,
  provider_reference text,
  idempotency_key text unique,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists touchpoints_company_idx
  on outreach.touchpoints(company_id, executed_at desc);

create index if not exists touchpoints_contact_idx
  on outreach.touchpoints(decision_maker_id, executed_at desc);

create index if not exists touchpoints_sequence_idx
  on outreach.touchpoints(sequence_id, scheduled_at);

create table if not exists outreach.execution_attempts (
  execution_attempt_id uuid primary key default gen_random_uuid(),
  touchpoint_id uuid not null references outreach.touchpoints(touchpoint_id) on delete cascade,
  attempt_number integer not null check (attempt_number > 0),
  provider text,
  result text not null,
  provider_error_code text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  unique(touchpoint_id, attempt_number)
);

create table if not exists ops.provider_credentials (
  credential_ref_id uuid primary key default gen_random_uuid(),
  provider text not null,
  purpose text not null,
  secret_manager_ref text not null,
  status text not null default 'active'
    check (status in ('active','cooldown','disabled','exhausted')),
  cooldown_until timestamptz,
  usage_snapshot jsonb not null default '{}'::jsonb,
  last_used_at timestamptz,
  last_error_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists ops.provider_pools (
  pool_id uuid primary key default gen_random_uuid(),
  provider text not null,
  pool_name text not null,
  selection_policy text not null default 'healthy_round_robin',
  enabled boolean not null default true,
  unique(provider, pool_name)
);

create table if not exists ops.provider_pool_members (
  pool_member_id uuid primary key default gen_random_uuid(),
  pool_id uuid not null references ops.provider_pools(pool_id) on delete cascade,
  credential_ref_id uuid not null references ops.provider_credentials(credential_ref_id) on delete cascade,
  ordinal integer not null,
  enabled boolean not null default true,
  cooldown_until timestamptz,
  consecutive_failures integer not null default 0 check (consecutive_failures >= 0),
  usage_snapshot jsonb not null default '{}'::jsonb,
  last_selected_at timestamptz,
  unique(pool_id, credential_ref_id),
  unique(pool_id, ordinal)
);

create table if not exists attribution.edges (
  edge_id uuid primary key default gen_random_uuid(),
  from_type text not null,
  from_id uuid not null,
  to_type text not null,
  to_id uuid not null,
  relationship text not null,
  occurred_at timestamptz not null default now(),
  evidence_event_id uuid,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists attribution_edges_from_idx
  on attribution.edges(from_type, from_id, occurred_at);

create index if not exists attribution_edges_to_idx
  on attribution.edges(to_type, to_id, occurred_at);

alter table growth.decision_makers enable row level security;
alter table growth.decision_maker_contact_methods enable row level security;
alter table growth.company_contacts enable row level security;
alter table intelligence.enrichment_runs enable row level security;
alter table intelligence.evidence enable row level security;
alter table intelligence.intent_signals enable row level security;
alter table intelligence.company_scores enable row level security;
alter table growth.campaigns enable row level security;
alter table growth.campaign_batches enable row level security;
alter table growth.campaign_company_enrollments enable row level security;
alter table growth.contact_campaign_states enable row level security;
alter table outreach.sequences enable row level security;
alter table outreach.sequence_approvals enable row level security;
alter table outreach.touchpoints enable row level security;
alter table outreach.execution_attempts enable row level security;
alter table ops.provider_credentials enable row level security;
alter table ops.provider_pools enable row level security;
alter table ops.provider_pool_members enable row level security;
alter table attribution.edges enable row level security;
