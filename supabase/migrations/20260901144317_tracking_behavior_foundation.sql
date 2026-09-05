create schema if not exists tracking;

alter table tracking.behavioral_events
  add column if not exists account_id text,
  add column if not exists correlation_id text,
  add column if not exists causation_id text,
  add column if not exists confidence numeric(4,3),
  add column if not exists automation_classification text default 'unknown',
  add column if not exists automation_reason text,
  add column if not exists source_event_id text,
  add column if not exists ingest_key text;

alter table tracking.behavioral_events
  drop constraint if exists behavioral_events_confidence_check;
alter table tracking.behavioral_events
  add constraint behavioral_events_confidence_check
  check (confidence is null or (confidence >= 0 and confidence <= 1));

alter table tracking.behavioral_events
  drop constraint if exists behavioral_events_automation_classification_check;
alter table tracking.behavioral_events
  add constraint behavioral_events_automation_classification_check
  check (automation_classification in ('automated','human_candidate','unknown'));

create unique index if not exists tracking_behavioral_source_event_uidx
  on tracking.behavioral_events(source_event_id)
  where source_event_id is not null;
create unique index if not exists tracking_behavioral_ingest_uidx
  on tracking.behavioral_events(ingest_key)
  where ingest_key is not null;
create index if not exists tracking_behavioral_account_time_idx
  on tracking.behavioral_events(account_id, occurred_at desc);
create index if not exists tracking_behavioral_event_name_time_idx
  on tracking.behavioral_events(event_name, occurred_at desc);
create index if not exists tracking_behavioral_human_candidate_idx
  on tracking.behavioral_events(person_id, occurred_at desc)
  where automation_classification <> 'automated';

alter table tracking.link_events
  add column if not exists account_id text,
  add column if not exists correlation_id text,
  add column if not exists causation_id text,
  add column if not exists confidence numeric(4,3) default 0.4,
  add column if not exists automation_classification text default 'unknown',
  add column if not exists automation_reason text,
  add column if not exists source_event_id text,
  add column if not exists ingest_key text,
  add column if not exists link_type text;

alter table tracking.link_events
  drop constraint if exists link_events_confidence_check;
alter table tracking.link_events
  add constraint link_events_confidence_check
  check (confidence is null or (confidence >= 0 and confidence <= 1));

alter table tracking.link_events
  drop constraint if exists link_events_automation_classification_check;
alter table tracking.link_events
  add constraint link_events_automation_classification_check
  check (automation_classification in ('automated','human_candidate','unknown'));

create unique index if not exists tracking_link_source_event_uidx
  on tracking.link_events(source_event_id)
  where source_event_id is not null;
create unique index if not exists tracking_link_ingest_uidx
  on tracking.link_events(ingest_key)
  where ingest_key is not null;
create index if not exists tracking_link_account_time_idx
  on tracking.link_events(account_id, occurred_at desc);
create index if not exists tracking_link_type_time_idx
  on tracking.link_events(link_type, occurred_at desc);

create table if not exists tracking.trackable_links (
  id uuid primary key default gen_random_uuid(),
  public_token text not null unique default encode(gen_random_bytes(24), 'hex'),
  send_id uuid references public.sends(id) on delete set null,
  person_id bigint references public.people(id) on delete set null,
  account_id text,
  campaign_id uuid references public.campaigns(id) on delete set null,
  link_type text not null default 'asset' check (link_type in ('asset','cta','website','unsubscribe','other')),
  destination_url text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  revoked_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  check (destination_url ~* '^https://')
);
create index if not exists tracking_trackable_links_send_idx on tracking.trackable_links(send_id);
create index if not exists tracking_trackable_links_campaign_idx on tracking.trackable_links(campaign_id);

create table if not exists tracking.asset_tokens (
  id uuid primary key default gen_random_uuid(),
  public_token text not null unique default encode(gen_random_bytes(24), 'hex'),
  send_id uuid references public.sends(id) on delete set null,
  person_id bigint references public.people(id) on delete set null,
  account_id text,
  campaign_id uuid references public.campaigns(id) on delete set null,
  asset_type text not null check (asset_type in ('loom','brief','landing','other')),
  asset_url text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  revoked_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  check (asset_url ~* '^https://')
);
create index if not exists tracking_asset_tokens_send_idx on tracking.asset_tokens(send_id);
create index if not exists tracking_asset_tokens_campaign_idx on tracking.asset_tokens(campaign_id);

create table if not exists tracking.sessions (
  session_id text primary key,
  person_id bigint references public.people(id) on delete set null,
  account_id text,
  campaign_id uuid references public.campaigns(id) on delete set null,
  send_id uuid references public.sends(id) on delete set null,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);
create index if not exists tracking_sessions_person_last_idx on tracking.sessions(person_id, last_seen_at desc);
create index if not exists tracking_sessions_account_last_idx on tracking.sessions(account_id, last_seen_at desc);

create or replace view tracking.v_behavioral_timeline as
select
  be.id as event_id,
  be.account_id,
  be.person_id,
  be.campaign_id,
  be.send_id,
  be.session_id,
  be.event_type,
  be.event_name,
  be.occurred_at,
  be.path,
  be.confidence,
  be.automation_classification,
  be.automation_reason,
  be.correlation_id,
  be.causation_id,
  be.metadata
from tracking.behavioral_events be;

create or replace view tracking.v_human_engagement as
select *
from tracking.v_behavioral_timeline
where automation_classification <> 'automated';

create or replace view tracking.v_link_engagement as
select
  le.id as event_id,
  le.account_id,
  le.person_id,
  le.campaign_id,
  le.send_id,
  le.link_id,
  le.link_type,
  le.occurred_at,
  le.confidence,
  le.automation_classification,
  le.automation_reason,
  le.user_agent,
  le.referrer,
  le.metadata
from tracking.link_events le;

alter table tracking.trackable_links enable row level security;
alter table tracking.asset_tokens enable row level security;
alter table tracking.sessions enable row level security;

-- Tracking data is only reachable through the server-side service role boundary.
-- RLS is enabled on durable tracking tables; no anonymous/authenticated policies
-- are added by Tracking, preventing direct browser reads/writes by default.
