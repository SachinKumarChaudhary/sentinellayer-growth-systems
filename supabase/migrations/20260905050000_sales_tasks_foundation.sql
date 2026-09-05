create schema if not exists sales;

create table if not exists sales.tasks (
  sales_task_id uuid primary key default gen_random_uuid(),
  account_id text not null,
  person_id text not null,
  trigger_type text not null,
  priority text not null check (priority in ('P1','P2','P3','P4')),
  recommended_action text not null,
  why_now jsonb not null default '[]'::jsonb,
  latest_reply jsonb,
  behavior_summary jsonb,
  campaign_context jsonb,
  conversation_summary jsonb,
  status text not null default 'open'
    check (status in ('open','claimed','completed','dismissed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists sales_tasks_account_person_trigger_idx
  on sales.tasks(account_id, person_id, trigger_type)
  where status in ('open','claimed');

alter table sales.tasks enable row level security;
