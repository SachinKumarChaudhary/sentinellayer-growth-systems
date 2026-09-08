-- Decision-maker verification + human approval gate for campaign enrollment.
-- Applied migrations remain immutable; this migration adds the enrollment guard.

create table if not exists public.campaign_decision_maker_reviews (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  person_id bigint not null references public.people(id) on delete restrict,
  ranking_score numeric(8,2) not null check (ranking_score >= 0),
  eligible boolean not null,
  verification_status text not null check (verification_status in ('unknown','candidate','verified','invalid','stale')),
  verification_provider text,
  approval_status text not null default 'pending' check (approval_status in ('pending','approved','rejected')),
  operator_id text,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  unique(campaign_id, person_id)
);

create index if not exists campaign_dm_reviews_status_idx
  on public.campaign_decision_maker_reviews(campaign_id, approval_status, ranking_score desc);

create or replace function public.approve_campaign_decision_maker_review(
  p_review_id uuid,
  p_operator_id text
)
returns public.campaign_decision_maker_reviews
language plpgsql
security definer
set search_path = public
as $$
declare
  r public.campaign_decision_maker_reviews%rowtype;
begin
  if p_operator_id is null or btrim(p_operator_id) = '' then
    raise exception 'operator_id is required';
  end if;

  select * into r
  from public.campaign_decision_maker_reviews
  where id = p_review_id
  for update;

  if not found then
    raise exception 'decision-maker review not found';
  end if;

  if not r.eligible then
    raise exception 'decision-maker is not eligible for enrollment';
  end if;

  if r.verification_status <> 'verified' then
    raise exception 'decision-maker contact is not verified';
  end if;

  if r.approval_status = 'rejected' then
    raise exception 'decision-maker review was rejected';
  end if;

  update public.campaign_decision_maker_reviews
  set approval_status = 'approved',
      operator_id = btrim(p_operator_id),
      approved_at = now()
  where id = p_review_id
  returning * into r;

  return r;
end;
$$;

create or replace function public.enforce_campaign_enrollment_gate()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  r public.campaign_decision_maker_reviews%rowtype;
begin
  if new.decision_maker_review_id is null then
    raise exception 'campaign enrollment requires decision-maker verification and operator approval';
  end if;

  select * into r
  from public.campaign_decision_maker_reviews
  where id = new.decision_maker_review_id
    and campaign_id = new.campaign_id
    and person_id = new.person_id;

  if not found then
    raise exception 'campaign enrollment references no matching decision-maker review';
  end if;

  if not r.eligible then
    raise exception 'campaign enrollment blocked: decision-maker is not eligible';
  end if;

  if r.verification_status <> 'verified' then
    raise exception 'campaign enrollment blocked: contact is not verified';
  end if;

  if r.approval_status <> 'approved' or r.operator_id is null or r.approved_at is null then
    raise exception 'campaign enrollment blocked: explicit operator approval is required';
  end if;

  return new;
end;
$$;

alter table public.campaign_enrollments
  add column if not exists decision_maker_review_id uuid references public.campaign_decision_maker_reviews(id) on delete restrict;

create index if not exists campaign_enrollments_dm_review_idx
  on public.campaign_enrollments(decision_maker_review_id);

drop trigger if exists campaign_enrollment_decision_maker_gate on public.campaign_enrollments;
create trigger campaign_enrollment_decision_maker_gate
before insert on public.campaign_enrollments
for each row execute function public.enforce_campaign_enrollment_gate();

alter table public.campaign_decision_maker_reviews enable row level security;

-- Approval is backend-controlled; clients do not receive a direct write policy.
