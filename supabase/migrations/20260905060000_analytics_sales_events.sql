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

create index if not exists analytics_sales_events_account_time_idx
  on analytics.sales_events(account_id, occurred_at desc);

create index if not exists analytics_sales_events_person_time_idx
  on analytics.sales_events(person_id, occurred_at desc)
  where person_id is not null;

alter table analytics.sales_events enable row level security;

-- Analytics events are backend-written for now; no client-facing policies.
