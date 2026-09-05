-- Repair the applied rendered-send migration for the text/bigint person-id boundary.
-- Keep this as a forward migration because 20260905110000 is already applied
-- on persistent integration databases.

drop function if exists public.claim_due_sends(integer, text);

create or replace function public.claim_due_sends(
  p_batch_size integer default 20,
  p_worker_id text default 'worker'
)
returns table(
  send_id uuid, person_id bigint, campaign_id uuid, sequence_step_id uuid,
  mailbox_id uuid, scheduled_at timestamptz, attempt_count integer,
  sender text, recipient text, subject text, body_text text, message_id text,
  rendered_headers jsonb, reply_to text
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
      and not exists (select 1 from conversation.replies r where r.person_id=s.person_id::text)
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
              s.rendered_subject,s.rendered_body_text,s.rendered_headers,s.reply_to
  )
  select cl.id,cl.person_id,cl.campaign_id,cl.sequence_step_id,cl.mailbox_id,cl.scheduled_at,
         cl.attempt_count,coalesce(cl.rendered_sender,m.email),coalesce(cl.rendered_recipient,p.email),
         coalesce(cl.rendered_subject,ss.subject_template),coalesce(cl.rendered_body_text,ss.body_template),
         cl.message_id,coalesce(cl.rendered_headers,'{}'::jsonb),cl.reply_to
  from claimed cl join public.people p on p.id=cl.person_id
  join public.sequence_steps ss on ss.id=cl.sequence_step_id
  join mail.mailboxes m on m.id=cl.mailbox_id;
end;
$function$;
