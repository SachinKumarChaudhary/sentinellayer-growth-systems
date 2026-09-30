create table if not exists crm.user_access (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null check (role in ('OPERATOR','REVIEWER','ADMIN')),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists crm_user_access_role_idx
  on crm.user_access(role)
  where active;

alter table crm.user_access enable row level security;

drop policy if exists crm_user_access_self_read on crm.user_access;
create policy crm_user_access_self_read
on crm.user_access
for select
to authenticated
using (user_id = auth.uid());

comment on table crm.user_access is
  'CRM application authorization membership. API routes require an active row; OPERATOR and ADMIN may mutate, REVIEWER is read-only.';
