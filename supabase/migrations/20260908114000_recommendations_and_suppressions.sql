create table if not exists growth.recommendations (
  recommendation_id uuid primary key default gen_random_uuid(),
  company_id bigint not null references public.companies(id) on delete cascade,
  decision_maker_id uuid references growth.decision_makers(decision_maker_id) on delete set null,
  recommendation_type text not null,
  recommended_channel text check (recommended_channel in ('email','linkedin','instagram','reddit','social_content','phone','none')),
  reason text not null,
  supporting_signal_ids uuid[] not null default '{}',
  recommended_sequence jsonb not null default '[]'::jsonb,
  draft_message text,
  confidence numeric(5,4) check (confidence between 0 and 1),
  requires_approval boolean not null default true,
  status text not null default 'pending'
    check (status in ('pending','approved','rejected','executed','expired')),
  created_at timestamptz not null default now(),
  expires_at timestamptz
);

create index if not exists recommendations_company_idx
  on growth.recommendations(company_id, status, created_at desc);

create table if not exists growth.suppressions (
  suppression_id uuid primary key default gen_random_uuid(),
  company_id bigint not null references public.companies(id) on delete cascade,
  decision_maker_id uuid references growth.decision_makers(decision_maker_id) on delete cascade,
  scope text not null check (scope in ('channel','campaign','global','company')),
  channel text check (channel is null or channel in ('email','linkedin','instagram','reddit','social_content','phone','website')),
  campaign_id uuid references growth.campaigns(campaign_id) on delete cascade,
  reason text not null,
  source text,
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  active boolean not null default true
);

create index if not exists suppressions_company_active_idx
  on growth.suppressions(company_id, active, created_at desc);

create index if not exists suppressions_dm_active_idx
  on growth.suppressions(decision_maker_id, active, created_at desc);

alter table growth.recommendations enable row level security;
alter table growth.suppressions enable row level security;
