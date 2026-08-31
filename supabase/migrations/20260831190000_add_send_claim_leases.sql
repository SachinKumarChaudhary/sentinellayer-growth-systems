alter table public.sends
  add column if not exists claim_lease_until timestamptz;

create index if not exists sends_claim_lease_idx
  on public.sends (claim_lease_until)
  where status = 'claiming';

-- Claim due queued sends and reclaim abandoned claims after the lease expires.
create or replace function public.claim_due_sends(
  p_batch_size integer default 20,
  p_worker_id text default 'worker'
)
returns table(
  send_id uuid, person_id bigint, campaign_id uuid, sequence_step_id uuid,
  mailbox_id uuid, scheduled_at timestamptz, attempt_count integer,
  sender text, recipient text, subject text, body_text text, message_id text
)
language plpgsql security definer
set search_path to 'public','mail'
as $function$
begin
  if p_batch_size < 1 or p_batch_size > 500 then raise exception 'p_batch_size must be between 1 and 500'; end if;
  if nullif(trim(p_worker_id), '') is null then raise exception 'p_worker_id is required'; end if;

  return query
  with candidates as (
    select s.id
    from public.sends s
    join public.people p on p.id=s.person_id
    join public.campaigns c on c.id=s.campaign_id
    join public.sequence_steps ss on ss.id=s.sequence_step_id
    join mail.mailboxes m on m.id=s.mailbox_id
    where (
      (s.status='queued' and coalesce(s.next_attempt_at,s.scheduled_at)<=now())
      or (s.status='claiming' and s.claim_lease_until is not null and s.claim_lease_until<=now())
    )
      and ss.active=true and c.status='active' and m.status='active'
      and m.health_status in ('healthy','unknown','caution')
      and nullif(trim(p.email),'') is not null
      and not public.is_suppressed(p.email)
      and not exists (select 1 from public.replies r where r.person_id=s.person_id)
      and (c.sending_window_start is null or c.sending_window_end is null
           or ((now() at time zone coalesce(nullif(m.timezone,''),c.timezone))::time)
              between c.sending_window_start and c.sending_window_end)
      and (c.daily_global_limit=0 or
           (select count(*) from public.sends sd where sd.campaign_id=c.id and sd.status='sent'
            and sd.sent_at>=date_trunc('day',now() at time zone c.timezone) at time zone c.timezone)<c.daily_global_limit)
      and (m.daily_limit=0 or
           (select count(*) from public.sends sd where sd.mailbox_id=m.id and sd.status='sent'
            and sd.sent_at>=date_trunc('day',now() at time zone m.timezone) at time zone m.timezone)<m.daily_limit)
    order by coalesce(s.next_attempt_at,s.scheduled_at),s.id
    for update of s skip locked limit p_batch_size
  ), claimed as (
    update public.sends s
    set status='claiming', claimed_at=now(), claimed_by=p_worker_id,
        claim_lease_until=now()+interval '10 minutes',
        attempt_count=s.attempt_count+1, attempted_at=now(),
        message_id=coalesce(s.message_id,'<'||s.id::text||'@'||
          (select d.domain_name from mail.mailboxes mm join mail.domains d on d.id=mm.domain_id where mm.id=s.mailbox_id)||'>')
    from candidates c where s.id=c.id
    returning s.id,s.person_id,s.campaign_id,s.sequence_step_id,s.mailbox_id,s.scheduled_at,s.attempt_count,s.message_id
  )
  select cl.id,cl.person_id,cl.campaign_id,cl.sequence_step_id,cl.mailbox_id,cl.scheduled_at,
         cl.attempt_count,m.email,p.email,ss.subject_template,ss.body_template,cl.message_id
  from claimed cl join public.people p on p.id=cl.person_id
  join public.sequence_steps ss on ss.id=cl.sequence_step_id
  join mail.mailboxes m on m.id=cl.mailbox_id;
end;
$function$;

create or replace function public.record_send_attempt(
  p_send_id uuid, p_outcome text, p_provider_message_id text default null,
  p_provider_code text default null, p_error_message text default null,
  p_retry_at timestamptz default null, p_metadata jsonb default '{}'::jsonb,
  p_worker_id text default null
)
returns public.sends language plpgsql security definer set search_path to 'public'
as $function$
declare v_send public.sends; v_attempt integer; v_status text;
begin
  select * into v_send from public.sends where id=p_send_id for update;
  if not found then raise exception 'send % not found',p_send_id; end if;
  if p_worker_id is not null and v_send.claimed_by is distinct from p_worker_id
    then raise exception 'claim ownership lost for send %',p_send_id; end if;

  v_attempt:=greatest(v_send.attempt_count,1);
  insert into public.send_attempts(send_id,attempt_no,finished_at,outcome,provider_message_id,provider_code,error_message,metadata)
  values(p_send_id,v_attempt,now(),p_outcome,p_provider_message_id,p_provider_code,p_error_message,coalesce(p_metadata,'{}'::jsonb))
  on conflict(send_id,attempt_no) do update set finished_at=excluded.finished_at,outcome=excluded.outcome,
    provider_message_id=excluded.provider_message_id,provider_code=excluded.provider_code,
    error_message=excluded.error_message,metadata=excluded.metadata;

  v_status:=case p_outcome when 'accepted' then 'sent' when 'temporary_failure' then 'queued'
    when 'permanent_failure' then 'failed' when 'provider_failure' then 'failed' else 'failed' end;
  update public.sends set status=v_status,
    sent_at=case when p_outcome='accepted' then now() else sent_at end,
    message_id=case when p_provider_message_id is not null then p_provider_message_id else message_id end,
    last_error=p_error_message,
    next_attempt_at=case when p_outcome='temporary_failure' then p_retry_at else null end,
    claimed_by=null, claim_lease_until=null
  where id=p_send_id returning * into v_send;
  return v_send;
end;
$function$;