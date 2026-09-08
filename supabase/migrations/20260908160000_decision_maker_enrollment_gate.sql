-- Consequential outreach gate: a decision-maker must have a provider-verified
-- contact and explicit operator approval before company enrollment.

create table if not exists growth.decision_maker_reviews (
  review_id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references growth.campaigns(campaign_id) on delete cascade,
  company_id bigint not null references public.companies(id) on delete cascade,
  decision_maker_id uuid not null references growth.decision_makers(decision_maker_id) on delete cascade,
  status text not null default 'pending'
    check (status in ('pending','approved','rejected','expired')),
  operator_id text,
  reviewed_at timestamptz,
  notes text,
  created_at timestamptz not null default now(),
  unique(campaign_id, decision_maker_id)
);

create index if not exists decision_maker_reviews_company_idx
  on growth.decision_maker_reviews(company_id, status, created_at desc);

alter table growth.campaign_company_enrollments
  add column if not exists decision_maker_id uuid
    references growth.decision_makers(decision_maker_id) on delete restrict,
  add column if not exists decision_maker_review_id uuid
    references growth.decision_maker_reviews(review_id) on delete restrict;

create index if not exists campaign_company_enrollments_dm_idx
  on growth.campaign_company_enrollments(decision_maker_id, status);

create or replace function growth.approve_decision_maker_review(
  p_review_id uuid,
  p_operator_id text,
  p_notes text default null
)
returns growth.decision_maker_reviews
language plpgsql
security definer
set search_path = growth, public
as $$
declare
  v_review growth.decision_maker_reviews;
  v_verified boolean;
begin
  if nullif(trim(coalesce(p_operator_id, '')), '') is null then
    raise exception 'operator_id is required for decision-maker approval';
  end if;

  select exists (
    select 1
    from growth.decision_maker_contact_methods cm
    where cm.decision_maker_id = v_review.decision_maker_id
      and cm.verification_status = 'verified'
  ) into v_verified;

  select * into v_review
  from growth.decision_maker_reviews
  where review_id = p_review_id
  for update;

  if not found then
    raise exception 'decision-maker review not found';
  end if;

  if not exists (
    select 1
    from growth.decision_maker_contact_methods cm
    where cm.decision_maker_id = v_review.decision_maker_id
      and cm.verification_status = 'verified'
  ) then
    raise exception 'decision-maker requires at least one verified contact before approval';
  end if;

  update growth.decision_maker_reviews
  set status = 'approved',
      operator_id = trim(p_operator_id),
      reviewed_at = now(),
      notes = p_notes
  where review_id = p_review_id
  returning * into v_review;

  return v_review;
end;
$$;

create or replace function growth.enforce_decision_maker_enrollment_gate()
returns trigger
language plpgsql
set search_path = growth, public
as $$
begin
  if new.decision_maker_id is null or new.decision_maker_review_id is null then
    raise exception 'campaign enrollment requires decision_maker_id and decision_maker_review_id';
  end if;

  if not exists (
    select 1
    from growth.decision_maker_reviews r
    where r.review_id = new.decision_maker_review_id
      and r.campaign_id = new.campaign_id
      and r.company_id = new.company_id
      and r.decision_maker_id = new.decision_maker_id
      and r.status = 'approved'
      and r.operator_id is not null
      and r.reviewed_at is not null
  ) then
    raise exception 'campaign enrollment blocked: operator approval is required';
  end if;

  if not exists (
    select 1
    from growth.decision_maker_contact_methods cm
    where cm.decision_maker_id = new.decision_maker_id
      and cm.verification_status = 'verified'
  ) then
    raise exception 'campaign enrollment blocked: verified contact is required';
  end if;

  return new;
end;
$$;

drop trigger if exists decision_maker_enrollment_gate
  on growth.campaign_company_enrollments;

create trigger decision_maker_enrollment_gate
before insert or update of campaign_id, company_id, decision_maker_id, decision_maker_review_id
on growth.campaign_company_enrollments
for each row execute function growth.enforce_decision_maker_enrollment_gate();

alter table growth.decision_maker_reviews enable row level security;
