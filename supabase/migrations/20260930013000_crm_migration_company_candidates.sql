create table if not exists crm.migration_company_candidates (
  candidate_id uuid primary key default gen_random_uuid(),
  source_name text not null,
  source_snapshot_hash text not null,
  source_row_number bigint not null,
  source_company_name text not null,
  normalized_company_name text not null,
  candidate_domain text,
  domain_source text,
  resolution_status text not null
    check (resolution_status in ('AUTO_CANDIDATE','REVIEW','UNRESOLVED','RESOLVED')),
  canonical_account_id bigint
    references public.companies(id) on delete set null,
  confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 1)),
  provenance jsonb not null default '{}'::jsonb
    check (jsonb_typeof(provenance) = 'object'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_name, source_snapshot_hash, source_row_number)
);

create index if not exists crm_migration_company_candidates_status_idx
  on crm.migration_company_candidates(resolution_status);

create index if not exists crm_migration_company_candidates_domain_idx
  on crm.migration_company_candidates(candidate_domain)
  where candidate_domain is not null;

alter table crm.migration_company_candidates enable row level security;
