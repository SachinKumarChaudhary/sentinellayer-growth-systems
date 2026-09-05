-- Compatibility wrapper for retention maintenance.
create or replace function tracking.purge_expired_behavioral_data(retention_days integer)
returns table (
  behavioral_deleted bigint,
  link_deleted bigint,
  sessions_deleted bigint
)
language sql
security invoker
set search_path = tracking, public
as $$
  select * from tracking.purge_expired_behavioral_data(p_retention_days => retention_days);
$$;

revoke all on function tracking.purge_expired_behavioral_data(integer) from public;
