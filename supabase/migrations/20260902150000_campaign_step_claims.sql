-- Campaign step claim protocol.
-- A claim prevents two campaign workers from rendering the same enrollment step.
-- Mail delivery remains outside this subsystem.

alter table public.campaign_enrollments
  add column if not exists step_claim_token uuid,
  add column if not exists step_claimed_at timestamptz,
  add column if not exists step_claim_lease_until timestamptz;

create index if not exists campaign_enrollments_claim_idx
  on public.campaign_enrollments(status, next_action_at, step_claim_lease_until);

create or replace function public.claim_campaign_step(
  p_enrollment_id uuid,
  p_worker_id text,
  p_lease_seconds integer default 300
)
returns table (
  enrollment_id uuid,
  campaign_id uuid,
  person_id bigint,
  account_id text,
  priority_at_enrollment text,
  strategy_version_id uuid,
  offer_version_id uuid,
  sequence_version_id uuid,
  experiment_variant_id uuid,
  step_claim_token uuid,
  sequence_step_id uuid,
  step_no integer,
  delay_days integer,
  message_version_id uuid,
  cta_version_id uuid,
  asset_policy jsonb,
  channel text,
  recipient_email text
)
language plpgsql
security definer
set search_path = public
as $$
declare
  e public.campaign_enrollments%rowtype;
  c public.campaigns%rowtype;
  q public.sequence_versions%rowtype;
  s public.sequence_steps%rowtype;
  p public.people%rowtype;
  v_token uuid;
begin
  if p_worker_id is null or btrim(p_worker_id) = '' then
    raise exception 'worker_id must not be empty';
  end if;
  if p_lease_seconds < 30 or p_lease_seconds > 3600 then
    raise exception 'lease_seconds must be between 30 and 3600';
  end if;

  select * into e
  from public.campaign_enrollments
  where id = p_enrollment_id
  for update;

  if not found then
    return;
  end if;

  if e.status not in ('pending','active') then
    return;
  end if;

  if e.next_action_at is not null and e.next_action_at > now() then
    return;
  end if;

  if e.step_claim_lease_until is not null and e.step_claim_lease_until > now() then
    return;
  end if;

  select * into c from public.campaigns where id=e.campaign_id;
  select * into q from public.sequence_versions where id=e.sequence_version_id;
  if not found or q.status not in ('reviewed','testing','active') then
    return;
  end if;

  if e.current_step_no >= q.max_steps then
    update public.campaign_enrollments
      set status='completed',
          terminated_at=coalesce(terminated_at, now()),
          termination_reason=coalesce(termination_reason, 'max_steps_reached'),
          step_claim_token=null,
          step_claimed_at=null,
          step_claim_lease_until=null
    where id=e.id;
    return;
  end if;

  select * into s
  from public.sequence_steps
  where sequence_version_id=e.sequence_version_id
    and step_no=e.current_step_no + 1
    and active=true
  for share;

  if not found then
    return;
  end if;

  if s.message_version_id is null or s.cta_version_id is null then
    return;
  end if;

  select * into p from public.people where id=e.person_id;
  if not found or p.email is null or btrim(p.email) = '' then
    return;
  end if;

  v_token := gen_random_uuid();

  update public.campaign_enrollments
  set step_claim_token=v_token,
      step_claimed_at=now(),
      step_claim_lease_until=now() + make_interval(secs => p_lease_seconds)
  where id=e.id;

  return query
  select e.id, e.campaign_id, e.person_id, e.account_id, e.priority_at_enrollment,
         e.strategy_version_id, e.offer_version_id, e.sequence_version_id,
         e.experiment_variant_id, v_token, s.id, s.step_no, s.delay_days,
         s.message_version_id, s.cta_version_id, s.asset_policy, s.channel, p.email;
end;
$$;

create or replace function public.release_campaign_step_claim(
  p_enrollment_id uuid,
  p_claim_token uuid
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.campaign_enrollments
  set step_claim_token=null,
      step_claimed_at=null,
      step_claim_lease_until=null
  where id=p_enrollment_id
    and step_claim_token=p_claim_token
    and status in ('pending','active');
  return found;
end;
$$;

create or replace function public.complete_campaign_step_claim(
  p_enrollment_id uuid,
  p_claim_token uuid,
  p_step_no integer,
  p_next_action_at timestamptz
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.campaign_enrollments
  set current_step_no=p_step_no,
      next_action_at=p_next_action_at,
      step_claim_token=null,
      step_claimed_at=null,
      step_claim_lease_until=null
  where id=p_enrollment_id
    and step_claim_token=p_claim_token
    and status in ('pending','active')
    and p_step_no=current_step_no + 1;
  return found;
end;
$$;
