create table if not exists intelligence.company_facts (
  company_id bigint primary key references public.companies(id) on delete cascade,
  employee_count integer check (employee_count is null or employee_count >= 0),
  monthly_sessions bigint check (monthly_sessions is null or monthly_sessions >= 0),
  has_login boolean not null default false,
  vertical text,
  ownership_type text,
  india_bridge boolean not null default false,
  data_sensitivity text,
  updated_at timestamptz not null default now()
);

alter table intelligence.company_facts enable row level security;
