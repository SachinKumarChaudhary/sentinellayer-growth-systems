create table if not exists public.campaign_strategies (
  id uuid primary key default gen_random_uuid(),
  strategy_key text not null unique,
  name text not null,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.strategy_versions (
  id uuid primary key default gen_random_uuid(),
  strategy_id uuid not null references public.campaign_strategies(id) on delete cascade,
  version_no integer not null check (version_no > 0),
  status text not null default 'draft' check (status in ('draft','reviewed','testing','active','retired')),
  hypothesis text,
  objective text,
  audience_definition jsonb not null default '{}'::jsonb,
  routing_policy jsonb not null default '{}'::jsonb,
  asset_policy jsonb not null default '{}'::jsonb,
  personalization_policy jsonb not null default '{}'::jsonb,
  experiment_policy jsonb not null default '{}'::jsonb,
  evidence_requirements jsonb not null default '{}'::jsonb,
  created_by text,
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  activated_at timestamptz,
  retired_at timestamptz,
  unique(strategy_id, version_no)
);
create index if not exists strategy_versions_status_idx on public.strategy_versions(strategy_id, status);

create table if not exists public.offer_versions (
  id uuid primary key default gen_random_uuid(),
  offer_key text not null,
  version_no integer not null check (version_no > 0),
  status text not null default 'draft' check (status in ('draft','reviewed','testing','active','retired')),
  name text not null,
  promise text,
  proof jsonb not null default '{}'::jsonb,
  value_equation jsonb not null default '{}'::jsonb,
  eligibility_rules jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  activated_at timestamptz,
  retired_at timestamptz,
  unique(offer_key, version_no)
);
create index if not exists offer_versions_active_idx on public.offer_versions(offer_key, status);

create table if not exists public.message_versions (
  id uuid primary key default gen_random_uuid(),
  message_key text not null,
  version_no integer not null check (version_no > 0),
  status text not null default 'draft' check (status in ('draft','reviewed','testing','active','retired')),
  angle_key text not null,
  subject_template text not null,
  body_template text not null,
  personalization_policy jsonb not null default '{}'::jsonb,
  evidence_requirements jsonb not null default '{}'::jsonb,
  channel text not null default 'email' check (channel in ('email','linkedin','loom','asset')),
  qa_status text not null default 'unreviewed' check (qa_status in ('unreviewed','approved','rejected')),
  created_at timestamptz not null default now(),
  activated_at timestamptz,
  retired_at timestamptz,
  unique(message_key, version_no)
);
create index if not exists message_versions_active_idx on public.message_versions(message_key, status);

create table if not exists public.cta_versions (
  id uuid primary key default gen_random_uuid(),
  cta_key text not null,
  version_no integer not null check (version_no > 0),
  status text not null default 'draft' check (status in ('draft','reviewed','testing','active','retired')),
  label text not null,
  action_type text not null check (action_type in ('reply','call','meeting','link','asset','none')),
  target text,
  friction_score numeric(5,2),
  constraints jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  activated_at timestamptz,
  retired_at timestamptz,
  unique(cta_key, version_no)
);
create index if not exists cta_versions_active_idx on public.cta_versions(cta_key, status);

create table if not exists public.sequence_versions (
  id uuid primary key default gen_random_uuid(),
  strategy_version_id uuid not null references public.strategy_versions(id) on delete restrict,
  sequence_key text not null,
  version_no integer not null check (version_no > 0),
  status text not null default 'draft' check (status in ('draft','reviewed','testing','active','retired')),
  name text not null,
  max_steps integer not null default 5 check (max_steps > 0),
  termination_policy jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  activated_at timestamptz,
  retired_at timestamptz,
  unique(sequence_key, version_no)
);
create index if not exists sequence_versions_strategy_idx on public.sequence_versions(strategy_version_id, status);

alter table public.sequence_steps
  add column if not exists sequence_version_id uuid references public.sequence_versions(id) on delete cascade,
  add column if not exists message_version_id uuid references public.message_versions(id) on delete restrict,
  add column if not exists cta_version_id uuid references public.cta_versions(id) on delete restrict,
  add column if not exists asset_policy jsonb not null default '{}'::jsonb,
  add column if not exists channel text not null default 'email' check (channel in ('email','linkedin','loom','asset'));

create index if not exists sequence_steps_version_idx on public.sequence_steps(sequence_version_id, step_no);

create table if not exists public.experiments (
  id uuid primary key default gen_random_uuid(),
  experiment_key text not null unique,
  name text not null,
  hypothesis text not null,
  status text not null default 'draft' check (status in ('draft','scheduled','running','paused','completed','cancelled')),
  allocation_method text not null default 'stable_hash' check (allocation_method in ('stable_hash','random','manual')),
  success_metric text not null,
  minimum_sample_size integer not null default 0 check (minimum_sample_size >= 0),
  started_at timestamptz,
  ended_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.experiment_variants (
  id uuid primary key default gen_random_uuid(),
  experiment_id uuid not null references public.experiments(id) on delete cascade,
  variant_key text not null,
  allocation_pct numeric(7,4) not null check (allocation_pct >= 0 and allocation_pct <= 100),
  strategy_version_id uuid references public.strategy_versions(id) on delete restrict,
  offer_version_id uuid references public.offer_versions(id) on delete restrict,
  sequence_version_id uuid references public.sequence_versions(id) on delete restrict,
  metadata jsonb not null default '{}'::jsonb,
  unique(experiment_id, variant_key)
);
create index if not exists experiment_variants_experiment_idx on public.experiment_variants(experiment_id);

alter table public.campaigns
  add column if not exists strategy_version_id uuid references public.strategy_versions(id) on delete restrict,
  add column if not exists offer_version_id uuid references public.offer_versions(id) on delete restrict,
  add column if not exists sequence_version_id uuid references public.sequence_versions(id) on delete restrict,
  add column if not exists experiment_id uuid references public.experiments(id) on delete set null,
  add column if not exists audience_definition jsonb not null default '{}'::jsonb;

create index if not exists campaigns_strategy_idx on public.campaigns(strategy_version_id);
create index if not exists campaigns_sequence_version_idx on public.campaigns(sequence_version_id);
create index if not exists campaigns_experiment_idx on public.campaigns(experiment_id);

create table if not exists public.campaign_enrollments (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  person_id bigint not null references public.people(id) on delete restrict,
  experiment_variant_id uuid references public.experiment_variants(id) on delete restrict,
  sequence_version_id uuid not null references public.sequence_versions(id) on delete restrict,
  strategy_version_id uuid not null references public.strategy_versions(id) on delete restrict,
  offer_version_id uuid references public.offer_versions(id) on delete restrict,
  status text not null default 'active' check (status in ('pending','active','paused','replied','completed','suppressed','bounced','cancelled')),
  current_step_no integer not null default 0 check (current_step_no >= 0),
  next_action_at timestamptz,
  enrolled_at timestamptz not null default now(),
  terminated_at timestamptz,
  termination_reason text,
  metadata jsonb not null default '{}'::jsonb,
  unique(campaign_id, person_id)
);
create index if not exists campaign_enrollments_due_idx on public.campaign_enrollments(status, next_action_at);
create index if not exists campaign_enrollments_person_idx on public.campaign_enrollments(person_id, enrolled_at desc);

create or replace function public.validate_campaign_configuration(p_campaign_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  c public.campaigns%rowtype;
  errors jsonb := '[]'::jsonb;
begin
  select * into c from public.campaigns where id = p_campaign_id;
  if not found then
    return jsonb_build_array(jsonb_build_object('code','campaign_not_found','message','Campaign does not exist'));
  end if;
  if c.strategy_version_id is null then
    errors := errors || jsonb_build_array(jsonb_build_object('code','missing_strategy_version','message','Campaign has no strategy version'));
  end if;
  if c.sequence_version_id is null then
    errors := errors || jsonb_build_array(jsonb_build_object('code','missing_sequence_version','message','Campaign has no sequence version'));
  end if;
  if c.strategy_version_id is not null and not exists (
    select 1 from public.strategy_versions sv
    where sv.id=c.strategy_version_id and sv.status in ('reviewed','testing','active')
  ) then
    errors := errors || jsonb_build_array(jsonb_build_object('code','invalid_strategy_version','message','Strategy version is not reviewable/testable/active'));
  end if;
  if c.sequence_version_id is not null and not exists (
    select 1 from public.sequence_versions qv
    where qv.id=c.sequence_version_id and qv.status in ('reviewed','testing','active')
  ) then
    errors := errors || jsonb_build_array(jsonb_build_object('code','invalid_sequence_version','message','Sequence version is not reviewable/testable/active'));
  end if;
  return errors;
end;
$$;

drop trigger if exists campaign_strategies_set_updated_at on public.campaign_strategies;
create trigger campaign_strategies_set_updated_at before update on public.campaign_strategies for each row execute function public.set_updated_at();

drop trigger if exists campaigns_set_updated_at on public.campaigns;
create trigger campaigns_set_updated_at before update on public.campaigns for each row execute function public.set_updated_at();

alter table public.campaign_strategies enable row level security;
alter table public.strategy_versions enable row level security;
alter table public.offer_versions enable row level security;
alter table public.message_versions enable row level security;
alter table public.cta_versions enable row level security;
alter table public.sequence_versions enable row level security;
alter table public.experiments enable row level security;
alter table public.experiment_variants enable row level security;
alter table public.campaign_enrollments enable row level security;

-- No client-facing policies are added yet. Strategy activation/enrollment is backend-controlled.
