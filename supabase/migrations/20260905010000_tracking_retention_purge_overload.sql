-- Retention purge compatibility marker.
-- The canonical function is defined by 20260902120000_tracking_privacy_retention.sql.
-- This migration intentionally performs no replacement because PostgreSQL cannot
-- alter an existing function's input parameter name with CREATE OR REPLACE.
do $ci$
begin
  if not exists (
    select 1
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'tracking'
      and p.proname = 'purge_expired_behavioral_data'
      and pg_get_function_identity_arguments(p.oid) = 'integer'
  ) then
    raise exception 'canonical tracking retention purge function is missing';
  end if;
end
$ci$;
