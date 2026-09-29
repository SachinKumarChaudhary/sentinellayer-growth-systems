create schema if not exists crm;

create table if not exists crm.account_state (
  account_id bigint primary key
    references public.companies(id) on delete cascade,
  state text not null
    check (state in (
      'NEW','QUALIFIED','WORKING','ENGAGED','FOLLOW_UP',
      'SALES_QUALIFIED','CUSTOMER','NOT_INTERESTED','NURTURE','SUPPRESSED'
    )),
  owner_user_id uuid,
  version bigint not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists crm.contact_state (
  decision_maker_id uuid primary key
    references growth.decision_makers(decision_maker_id) on delete cascade,
  state text not null
    check (state in (
      'NOT_CONTACTED','CONTACTED','CONNECTED','REPLIED',
      'FOLLOW_UP','SUPPRESSED'
    )),
  owner_user_id uuid,
  version bigint not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);create table if not exists crm.notes (
  note_id uuid primary key default gen_random_uuid(),
  account_id bigint references public.companies(id) on delete cascade,
  decision_maker_id uuid
    references growth.decision_makers(decision_maker_id) on delete cascade,
  body text not null check (btrim(body) <> ''),
  author_user_id uuid not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((account_id is not null) <> (decision_maker_id is not null))
);

create table if not exists crm.state_history (
  history_id uuid primary key default gen_random_uuid(),
  entity_type text not null
    check (entity_type in ('account','contact')),
  entity_id text not null,
  from_state text,
  to_state text not null,
  reason text,
  actor_user_id uuid,
  request_id text,
  metadata jsonb not null default '{}'::jsonb
    check (jsonb_typeof(metadata) = 'object'),
  occurred_at timestamptz not null default now()
);

create index if not exists crm_state_history_entity_idx
  on crm.state_history(entity_type, entity_id, occurred_at desc);

create table if not exists crm.audit_events (
  audit_id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id text not null,
  action text not null,  actor_user_id uuid,
  request_id text,
  idempotency_key text,
  before_json jsonb,
  after_json jsonb,
  metadata jsonb not null default '{}'::jsonb
    check (jsonb_typeof(metadata) = 'object'),
  created_at timestamptz not null default now()
);

create index if not exists crm_audit_events_entity_idx
  on crm.audit_events(entity_type, entity_id, created_at desc);

create index if not exists crm_audit_events_request_idx
  on crm.audit_events(request_id)
  where request_id is not null;

create table if not exists crm.migration_rows (
  migration_row_id uuid primary key default gen_random_uuid(),
  source_name text not null,
  source_snapshot_hash text not null,
  source_row_number bigint not null,
  source_row_hash text not null,
  raw_row jsonb not null,
  parser_result jsonb not null default '{}'::jsonb,
  disposition text not null
    check (disposition in ('imported','updated','merged','quarantined','rejected')),
  account_id bigint
    references public.companies(id) on delete set null,  decision_maker_id uuid
    references growth.decision_makers(decision_maker_id) on delete set null,
  target_activity_id uuid,
  target_task_id uuid,
  errors jsonb not null default '[]'::jsonb
    check (jsonb_typeof(errors) = 'array'),
  importer_version text not null,
  created_at timestamptz not null default now(),
  unique (source_name, source_snapshot_hash, source_row_number)
);

create index if not exists crm_migration_rows_snapshot_idx
  on crm.migration_rows(source_name, source_snapshot_hash);

alter table sales.tasks
  add column if not exists canonical_account_id bigint
    references public.companies(id) on delete restrict,
  add column if not exists canonical_person_id uuid
    references growth.decision_makers(decision_maker_id) on delete restrict,
  add column if not exists due_at timestamptz,
  add column if not exists assigned_to uuid,
  add column if not exists completed_at timestamptz,
  add column if not exists source_event_type text,
  add column if not exists source_event_id text,
  add column if not exists version bigint not null default 1;

create index if not exists sales_tasks_crm_queue_idx
  on sales.tasks(status, due_at, assigned_to, created_at desc);create unique index if not exists sales_tasks_canonical_active_idx
  on sales.tasks(
    canonical_account_id,
    coalesce(canonical_person_id, '00000000-0000-0000-0000-000000000000'::uuid),
    trigger_type
  )
  where status in ('open','claimed')
    and canonical_account_id is not null;

alter table conversation.threads
  add column if not exists canonical_account_id bigint
    references public.companies(id) on delete restrict,
  add column if not exists canonical_person_id uuid
    references growth.decision_makers(decision_maker_id) on delete restrict;

alter table conversation.replies
  add column if not exists canonical_account_id bigint
    references public.companies(id) on delete restrict,
  add column if not exists canonical_person_id uuid
    references growth.decision_makers(decision_maker_id) on delete restrict;

create index if not exists conversation_threads_canonical_account_idx
  on conversation.threads(canonical_account_id, last_message_at desc);

create index if not exists conversation_replies_canonical_account_idx
  on conversation.replies(canonical_account_id, received_at desc);update sales.tasks
set canonical_account_id = case
  when account_id ~ '^[0-9]+$' then account_id::bigint
  else null
end
where canonical_account_id is null
  and account_id ~ '^[0-9]+$';

update sales.tasks
set canonical_person_id = person_id::uuid
where canonical_person_id is null
  and person_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$';

update conversation.threads
set canonical_account_id = account_id::bigint
where canonical_account_id is null
  and account_id ~ '^[0-9]+$';

update conversation.threads
set canonical_person_id = person_id::uuid
where canonical_person_id is null
  and person_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$';update conversation.replies
set canonical_account_id = account_id::bigint
where canonical_account_id is null
  and account_id ~ '^[0-9]+$';

update conversation.replies
set canonical_person_id = person_id::uuid
where canonical_person_id is null
  and person_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$';

create or replace function crm.prevent_append_only_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'CRM append-only record cannot be updated or deleted';
end;
$$;

drop trigger if exists state_history_append_only on crm.state_history;
create trigger state_history_append_only
before update or delete on crm.state_history
for each row execute function crm.prevent_append_only_mutation();

drop trigger if exists audit_events_append_only on crm.audit_events;
create trigger audit_events_append_only
before update or delete on crm.audit_events
for each row execute function crm.prevent_append_only_mutation();

alter table crm.account_state enable row level security;
alter table crm.contact_state enable row level security;
alter table crm.notes enable row level security;
alter table crm.state_history enable row level security;
alter table crm.audit_events enable row level security;
alter table crm.migration_rows enable row level security;alter table sales.tasks
  alter column person_id drop not null;

create unique index if not exists crm_audit_events_idempotency_key_idx
  on crm.audit_events(idempotency_key)
  where idempotency_key is not null;

comment on column sales.tasks.canonical_account_id is
  'CRM canonical account FK; legacy account_id remains during compatibility period.';

comment on column sales.tasks.canonical_person_id is
  'CRM canonical decision-maker FK; legacy person_id remains during compatibility period.';comment on column conversation.threads.canonical_account_id is
  'CRM canonical account FK; legacy account_id remains during compatibility period.';

comment on column conversation.threads.canonical_person_id is
  'CRM canonical decision-maker FK; legacy person_id remains during compatibility period.';

comment on column conversation.replies.canonical_account_id is
  'CRM canonical account FK; legacy account_id remains during compatibility period.';

comment on column conversation.replies.canonical_person_id is
  'CRM canonical decision-maker FK; legacy person_id remains during compatibility period.';
