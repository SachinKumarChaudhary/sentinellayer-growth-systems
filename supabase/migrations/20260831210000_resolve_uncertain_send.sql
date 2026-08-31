create or replace function public.resolve_uncertain_send(
  p_send_id uuid,
  p_accepted boolean,
  p_provider_message_id text default null,
  p_error_message text default null
)
returns public.sends
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  v_send public.sends;
begin
  select * into v_send
  from public.sends
  where id = p_send_id
    and status = 'uncertain'
  for update;

  if not found then
    raise exception 'send % is not uncertain or does not exist', p_send_id;
  end if;

  update public.sends
  set status = case when p_accepted then 'sent' else 'failed' end,
      sent_at = case when p_accepted then coalesce(sent_at, now()) else sent_at end,
      message_id = coalesce(p_provider_message_id, message_id),
      last_error = case when p_accepted then null else p_error_message end,
      claimed_by = null,
      claim_lease_until = null,
      next_attempt_at = null
  where id = p_send_id
  returning * into v_send;

  return v_send;
end;
$function$;