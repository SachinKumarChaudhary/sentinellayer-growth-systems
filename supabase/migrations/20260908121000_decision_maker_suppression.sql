-- Decision-maker suppression is explicit and narrow.
-- The outreach policy currently suppresses CISO contacts only.

create table if not exists growth.decision_maker_suppressions (
  suppression_id uuid primary key default gen_random_uuid(),
  decision_maker_id uuid not null references growth.decision_makers(decision_maker_id) on delete cascade,
  reason text not null,
  scope text not null default 'global'
    check (scope in ('global','campaign','channel')),
  campaign_id uuid references growth.campaigns(campaign_id) on delete cascade,
  channel text check (channel in ('email','linkedin','instagram','reddit','x','phone','social_content')),
  created_by text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  check ((scope = 'global' and campaign_id is null and channel is null)
      or (scope = 'campaign' and campaign_id is not null and channel is null)
      or (scope = 'channel' and channel is not null and campaign_id is null))
);

create unique index if not exists decision_maker_global_suppression_uq
  on growth.decision_maker_suppressions(decision_maker_id)
  where scope = 'global';

create index if not exists decision_maker_suppression_lookup_idx
  on growth.decision_maker_suppressions(decision_maker_id, scope);

alter table growth.decision_maker_suppressions enable row level security;
