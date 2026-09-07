create table if not exists conversation.analysis_jobs (
  analysis_id uuid primary key default gen_random_uuid(),
  reply_id uuid not null unique references conversation.replies(reply_id) on delete cascade,
  status text not null default 'pending'
    check (status in ('pending','processing','completed','failed')),
  attempt_count integer not null default 0
    check (attempt_count >= 0),
  lease_owner text,
  lease_until timestamptz,
  provider text,
  model text,
  analysis jsonb,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists conversation_analysis_jobs_claim_idx
  on conversation.analysis_jobs(status, lease_until, created_at);

alter table conversation.analysis_jobs enable row level security;
