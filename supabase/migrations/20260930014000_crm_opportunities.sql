create table if not exists crm.opportunities (
  opportunity_id uuid primary key default gen_random_uuid(),
  account_id bigint not null references public.companies(id) on delete restrict,
  primary_contact_id uuid references growth.decision_makers(decision_maker_id) on delete set null,
  owner_user_id uuid not null references crm.user_access(user_id) on delete restrict,
  name text not null check (btrim(name) <> ''),
  stage text not null check (stage in (
    'QUALIFIED','DISCOVERY','EVALUATION','PROPOSAL','NEGOTIATION','WON','LOST'
  )),
  value numeric(18,2),
  currency text,
  expected_close_date date,
  next_task_id uuid references sales.tasks(sales_task_id) on delete set null,
  notes text,
  closed_at timestamptz,
  closed_reason text,
  version bigint not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (stage not in ('WON','LOST') or closed_at is not null),
  check (stage <> 'LOST' or nullif(btrim(closed_reason),'') is not null)
);

create index if not exists crm_opportunities_account_idx
  on crm.opportunities(account_id, stage, updated_at desc);
create index if not exists crm_opportunities_owner_idx
  on crm.opportunities(owner_user_id, stage, updated_at desc);
create index if not exists crm_opportunities_stage_idx
  on crm.opportunities(stage, updated_at desc);

alter table crm.opportunities enable row level security;

create or replace function crm.validate_opportunity_contact()
returns trigger
language plpgsql
set search_path = pg_catalog
as $$
begin
  if new.primary_contact_id is not null and not exists (
    select 1
    from growth.decision_makers dm
    where dm.decision_maker_id = new.primary_contact_id
      and dm.company_id = new.account_id
  ) then
    raise exception 'primary contact must belong to opportunity account';
  end if;
  return new;
end;
$$;

drop trigger if exists opportunity_contact_check on crm.opportunities;
create trigger opportunity_contact_check
before insert or update of account_id, primary_contact_id
on crm.opportunities
for each row execute function crm.validate_opportunity_contact();

create or replace function crm.validate_opportunity_stage()
returns trigger
language plpgsql
set search_path = pg_catalog
as $$
begin
  if new.stage in ('WON','LOST') and new.closed_at is null then
    raise exception 'closed_at is required for closed opportunity';
  end if;
  if new.stage = 'LOST' and nullif(btrim(new.closed_reason),'') is null then
    raise exception 'closed_reason is required for LOST opportunity';
  end if;
  if new.stage <> 'LOST' and new.closed_reason is not null then
    new.closed_reason := null;
  end if;
  return new;
end;
$$;

drop trigger if exists opportunity_stage_check on crm.opportunities;
create trigger opportunity_stage_check
before insert or update of stage, closed_at, closed_reason
on crm.opportunities
for each row execute function crm.validate_opportunity_stage();