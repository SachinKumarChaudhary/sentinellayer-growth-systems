alter table public.sends drop constraint if exists sends_status_check;
alter table public.sends add constraint sends_status_check
  check (status = any (array['queued','claiming','sending','sent','failed','cancelled','uncertain']));

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
  if p_worker_id is not null and v_send.claimed_by is distinct from p_worker_id then raise exception 'claim ownership lost for send %',p_send_id; end if;
  v_attempt:=greatest(v_send.attempt_count,1);
  insert into public.send_attempts(send_id,attempt_no,finished_at,outcome,provider_message_id,provider_code,error_message,metadata)
  values(p_send_id,v_attempt,now(),p_outcome,p_provider_message_id,p_provider_code,p_error_message,coalesce(p_metadata,'{}'::jsonb))
  on conflict(send_id,attempt_no) do update set finished_at=excluded.finished_at,outcome=excluded.outcome,
    provider_message_id=excluded.provider_message_id,provider_code=excluded.provider_code,error_message=excluded.error_message,metadata=excluded.metadata;
  v_status:=case p_outcome when 'accepted' then 'sent' when 'temporary_failure' then 'queued'
    when 'permanent_failure' then 'failed' when 'provider_failure' then 'failed'
    when 'ambiguous' then 'uncertain' else 'failed' end;
  update public.sends set status=v_status,
    sent_at=case when p_outcome='accepted' then now() else sent_at end,
    message_id=case when p_provider_message_id is not null then p_provider_message_id else message_id end,
    last_error=p_error_message,
    next_attempt_at=case when p_outcome='temporary_failure' then p_retry_at else null end,
    claimed_by=case when p_outcome='ambiguous' then claimed_by else null end,
    claim_lease_until=case when p_outcome='ambiguous' then claim_lease_until else null end
  where id=p_send_id returning * into v_send;
  return v_send;
end;
$function$;