-- Ensure the canonical retention purge function exists on legacy integration
-- databases where migration history may claim the policy migration was applied
-- even though the function was not present.
create or replace function tracking.purge_expired_behavioral_data(
  retention_days integer default 180
)
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
  v_behavioral bigint := 0;
  v_link bigint := 0;
  v_sessions bigint := 0;
  v_cutoff timestamptz;
begin
  if retention_days <= 0 then
    raise exception 'retention_days must be positive';
  end if;

  v_cutoff := now() - make_interval(days => retention_days);

  delete from tracking.behavioral_events
   where occurred_at < v_cutoff;
  get diagnostics v_behavioral = row_count;

  delete from tracking.link_events
   where occurred_at < v_cutoff;
  get diagnostics v_link = row_count;

  delete from tracking.sessions
   where last_seen_at < v_cutoff;
  get diagnostics v_sessions = row_count;

  return query select v_behavioral, v_link, v_sessions;
end;
$$;

revoke all on function tracking.purge_expired_behavioral_data(integer) from public;
