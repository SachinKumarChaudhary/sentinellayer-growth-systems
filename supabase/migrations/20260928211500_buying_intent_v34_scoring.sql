-- Reconcile deterministic scoring persistence with Buying Intent v3.4.
-- FIT remains structural/ICP context; INTENT is dated/decaying; behavior and
-- routing modifiers remain separate and auditable.

alter table intelligence.company_scores
  add column if not exists fit_raw numeric(8,2) not null default 0
    check (fit_raw >= 0),
  add column if not exists raw_intent numeric(8,4) not null default 0
    check (raw_intent >= 0),
  add column if not exists intent_components jsonb not null default '[]'::jsonb,
  add column if not exists behavior_stage text,
  add column if not exists behavior_identity text,
  add column if not exists behavior_timestamp timestamptz,
  add column if not exists next_review_date date;

alter table intelligence.company_scores
  drop constraint if exists company_scores_priority_check;

alter table intelligence.company_scores
  add constraint company_scores_priority_check
  check (priority in ('P1','P2','P3','P4'));

alter table intelligence.company_scores
  alter column scoring_version set default 'v3.4-exec1';

update intelligence.company_scores
set scoring_version = 'v3.4-exec1'
where scoring_version is null or scoring_version <> 'v3.4-exec1';
