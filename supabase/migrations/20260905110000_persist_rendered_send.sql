-- Persist exact rendered Campaign content on public.sends.
alter table public.sends
  add column if not exists rendered_sender text,
  add column if not exists rendered_recipient text,
  add column if not exists rendered_subject text,
  add column if not exists rendered_body_text text,
  add column if not exists rendered_headers jsonb not null default '{}'::jsonb,
  add column if not exists reply_to text;

create or replace function mail.enqueue_campaign_send(
  p_send_id uuid,
  p_idempotency_key text,
  p_campaign_id uuid,
  p_person_id bigint,
  p_sequence_step_id uuid,
  p_mailbox_id uuid,
  p_scheduled_at timestamptz,
  p_recipient text,
  p_subject text,
  p_body_text text,
  p_headers jsonb default '{}'::jsonb,
  p_reply_to text default null,
  p_metadata jsonb default '{}'::jsonb
)
returns public.sends
language plpgsql
security definer
set search_path = public, mail
as $function$
declare
  v_existing public.sends;
  v_row public.sends;
begin
  if nullif(trim(p_idempotency_key), '') is null then raise exception 'idempotency_key is required'; end if;
  if not exists (select 1 from mail.mailboxes m where m.id=p_mailbox_id and m.status='active' and nullif(trim(m.email),'') is not null) then raise exception 'mailbox is not active'; end if;
  if nullif(trim(p_recipient), '') is null then raise exception 'recipient is required'; end if;
  if nullif(trim(p_subject), '') is null then raise exception 'subject is required'; end if;
  if nullif(trim(p_body_text), '') is null then raise exception 'body_text is required'; end if;
  if p_scheduled_at is null then raise exception 'scheduled_at is required'; end if;
  if public.is_suppressed(p_recipient) then raise exception 'recipient is suppressed'; end if;
  if exists (select 1 from public.replies r where r.person_id = p_person_id) then
    raise exception 'person has an inbound reply; future cold sends are blocked';
  end if;

  select * into v_existing from public.sends where idempotency_key = p_idempotency_key for update;
  if found then
    if v_existing.campaign_id is distinct from p_campaign_id
       or v_existing.person_id is distinct from p_person_id
       or v_existing.sequence_step_id is distinct from p_sequence_step_id
       or v_existing.mailbox_id is distinct from p_mailbox_id
       or v_existing.scheduled_at is distinct from p_scheduled_at
       or v_existing.rendered_recipient is distinct from p_recipient
       or v_existing.rendered_subject is distinct from p_subject
       or v_existing.rendered_body_text is distinct from p_body_text then
      raise exception 'idempotency key collision with different send payload';
    end if;
    return v_existing;
  end if;

  insert into public.sends (
    id, person_id, campaign_id, sequence_step_id, mailbox_id,
    idempotency_key, scheduled_at, status, attempt_count,
    rendered_sender, rendered_recipient, rendered_subject,
    rendered_body_text, rendered_headers, reply_to, metadata
  ) values (
    p_send_id, p_person_id, p_campaign_id, p_sequence_step_id, p_mailbox_id,
    p_idempotency_key, p_scheduled_at, 'queued', 0,
    (select m.email from mail.mailboxes m where m.id=p_mailbox_id), p_recipient, p_subject, p_body_text,
    coalesce(p_headers, '{}'::jsonb), p_reply_to, coalesce(p_metadata, '{}'::jsonb)
  ) returning * into v_row;
  return v_row;
end;
$function$;

revoke all on function mail.enqueue_campaign_send(uuid,text,uuid,bigint,uuid,uuid,timestamptz,text,text,text,jsonb,text,jsonb) from public;
grant execute on function mail.enqueue_campaign_send(uuid,text,uuid,bigint,uuid,uuid,timestamptz,text,text,text,jsonb,text,jsonb) to service_role;

create or replace function public.claim_due_sends(
  p_batch_size integer default 20,
  p_worker_id text default 'worker'
)
returns table(
  send_id uuid, person_id bigint, campaign_id uuid, sequence_step_id uuid,
  mailbox_id uuid, scheduled_at timestamptz, attempt_count integer,
  sender text, recipient text, subject text, body_text text, message_id text
)
language plpgsql security definer set search_path to 'public','mail'
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
    where ((s.status='queued' and coalesce(s.next_attempt_at,s.scheduled_at)<=now())
       or (s.status='claiming' and s.claim_lease_until is not null and s.claim_lease_until<=now()))
      and ss.active=true and c.status='active' and m.status='active'
      and m.health_status in ('healthy','unknown','caution')
      and nullif(trim(coalesce(s.rendered_recipient,p.email)),'') is not null
      and not public.is_suppressed(coalesce(s.rendered_recipient,p.email))
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
        claim_lease_until=now()+interval '10 minutes', attempt_count=s.attempt_count+1,
        attempted_at=now(),
        message_id=coalesce(s.message_id,'<'||s.id::text||'@'||
          (select d.domain_name from mail.mailboxes mm join mail.domains d on d.id=mm.domain_id where mm.id=s.mailbox_id)||'>')
    from candidates c where s.id=c.id
    returning s.id,s.person_id,s.campaign_id,s.sequence_step_id,s.mailbox_id,s.scheduled_at,
              s.attempt_count,s.message_id,s.rendered_sender,s.rendered_recipient,
              s.rendered_subject,s.rendered_body_text
  )
  select cl.id,cl.person_id,cl.campaign_id,cl.sequence_step_id,cl.mailbox_id,cl.scheduled_at,
         cl.attempt_count,coalesce(cl.rendered_sender,m.email),coalesce(cl.rendered_recipient,p.email),
         coalesce(cl.rendered_subject,ss.subject_template),coalesce(cl.rendered_body_text,ss.body_template),cl.message_id
  from claimed cl join public.people p on p.id=cl.person_id
  join public.sequence_steps ss on ss.id=cl.sequence_step_id
  join mail.mailboxes m on m.id=cl.mailbox_id;
end;
$function$;
