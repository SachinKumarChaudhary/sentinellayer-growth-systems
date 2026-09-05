create schema if not exists analytics;

create table if not exists analytics.sales_events (
  event_id uuid primary key default gen_random_uuid(),
  event_type text not null,
  account_id text not null,
  person_id text,
  occurred_at timestamptz not null,
  attribution jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists analytics_sales_events_lineage_idx
  on analytics.sales_events(campaign_id)
  where false;
