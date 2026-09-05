-- Compatibility wrapper: expose the retention primitive under the exact signature
-- used by the Supabase integration gate.
create or replace function tracking.purge_expired_behavioral_data(p_retention_days integer)
returns table (
  behavioral_deleted bigint,
  link_deleted bigint,
  sessions_deleted bigint
)
language plpgsql
security invoker
set search_path = tracking, public
as $$
declare
  v_cutoff timestamptz;
begin
  if p_retention_days <= 0 then
    raise exception 'retention_days must be positive';
  end if;

  v_cutoff := now() - make_interval(days => p_retention_days);

  delete from tracking.behavioral_events where occurred_at < v_cutoff;
  get diagnostics behavioral_deleted = row_count;

  delete from tracking.link_events where occurred_at < v_cutoff;
  get diagnostics link_deleted = row_count;

  delete from tracking.sessions where last_seen_at < v_cutoff;
  get diagnostics sessions_deleted = row_count;

  return next;
end;
$$;

revoke all on function tracking.purge_expired_behavioral_data(integer) from public;
