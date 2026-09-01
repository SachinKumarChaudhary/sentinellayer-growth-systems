-- Campaign activation hardening.
-- Never rewrite an applied migration; add constraints/indexes here.

create unique index if not exists sequence_steps_version_step_active_uidx
  on public.sequence_steps(sequence_version_id, step_no)
  where active = true and sequence_version_id is not null;

create or replace function public.validate_campaign_configuration(p_campaign_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  c public.campaigns%rowtype;
  errors jsonb := '[]'::jsonb;
  step_count integer := 0;
  bad_steps integer := 0;
begin
  select * into c from public.campaigns where id = p_campaign_id;
  if not found then
    return jsonb_build_array(jsonb_build_object(
      'code','campaign_not_found','message','Campaign does not exist'
    ));
  end if;

  if c.strategy_version_id is null then
    errors := errors || jsonb_build_array(jsonb_build_object(
      'code','missing_strategy_version','message','Campaign has no strategy version'
    ));
  end if;

  if c.sequence_version_id is null then
    errors := errors || jsonb_build_array(jsonb_build_object(
      'code','missing_sequence_version','message','Campaign has no sequence version'
    ));
  end if;

  if c.strategy_version_id is not null and not exists (
    select 1 from public.strategy_versions sv
    where sv.id=c.strategy_version_id
      and sv.status in ('reviewed','testing','active')
  ) then
    errors := errors || jsonb_build_array(jsonb_build_object(
      'code','invalid_strategy_version',
      'message','Strategy version is not reviewable/testable/active'
    ));
  end if;

  if c.offer_version_id is not null and not exists (
    select 1 from public.offer_versions ov
    where ov.id=c.offer_version_id
      and ov.status in ('reviewed','testing','active')
  ) then
    errors := errors || jsonb_build_array(jsonb_build_object(
      'code','invalid_offer_version',
      'message','Offer version is not reviewable/testable/active'
    ));
  end if;

  if c.sequence_version_id is not null and not exists (
    select 1 from public.sequence_versions qv
    where qv.id=c.sequence_version_id
      and qv.status in ('reviewed','testing','active')
  ) then
    errors := errors || jsonb_build_array(jsonb_build_object(
      'code','invalid_sequence_version',
      'message','Sequence version is not reviewable/testable/active'
    ));
  end if;

  if c.sequence_version_id is not null then
    select count(*),
           count(*) filter (
             where message_version_id is null
                or cta_version_id is null
                or channel is null
                or channel not in ('email','linkedin','loom','asset')
           )
      into step_count, bad_steps
      from public.sequence_steps
      where sequence_version_id=c.sequence_version_id
        and active=true;

    if step_count = 0 then
      errors := errors || jsonb_build_array(jsonb_build_object(
        'code','no_active_sequence_steps','message','Sequence has no active steps'
      ));
    end if;

    if bad_steps > 0 then
      errors := errors || jsonb_build_array(jsonb_build_object(
        'code','invalid_sequence_steps',
        'message',format('%s active sequence step(s) are missing required version/channel references', bad_steps)
      ));
    end if;

    if exists (
      select 1
      from public.sequence_steps ss
      join public.message_versions mv on mv.id=ss.message_version_id
      where ss.sequence_version_id=c.sequence_version_id
        and ss.active=true
        and (mv.status not in ('reviewed','testing','active') or mv.qa_status <> 'approved')
    ) then
      errors := errors || jsonb_build_array(jsonb_build_object(
        'code','invalid_message_versions',
        'message','At least one active sequence step references a message version that is not QA approved/renderable'
      ));
    end if;

    if exists (
      select 1
      from public.sequence_steps ss
      join public.cta_versions cv on cv.id=ss.cta_version_id
      where ss.sequence_version_id=c.sequence_version_id
        and ss.active=true
        and cv.status not in ('reviewed','testing','active')
    ) then
      errors := errors || jsonb_build_array(jsonb_build_object(
        'code','invalid_cta_versions',
        'message','At least one active sequence step references a non-renderable CTA version'
      ));
    end if;
  end if;

  return errors;
end;
$$;
