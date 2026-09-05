-- Tracking privacy/retention controls.
-- Policy: raw behavioral/link/session records are retained for 180 days by default.
-- This migration deliberately does NOT delete rows automatically; Operations must
-- schedule the approved maintenance job after policy approval.
-- Public tokens are revoked rather than deleted when operationally necessary.
-- IP hashes are treated as derived identifiers and are not exposed by tracking views.

create index if not exists tracking_behavioral_retention_idx
  on tracking.behavioral_events(occurred_at);
create index if not exists tracking_link_retention_idx
  on tracking.link_events(occurred_at);
create index if not exists tracking_sessions_retention_idx
  on tracking.sessions(last_seen_at);

create or replace view tracking.v_behavioral_timeline as
select
  be.id as event_id,
  be.account_id,
  be.person_id,
  be.campaign_id,
  be.send_id,
  be.session_id,
  be.event_type,
  be.event_name,
  be.occurred_at,
  be.path,
  be.confidence,
  be.automation_classification,
  be.automation_reason,
  be.correlation_id,
  be.causation_id,
  be.metadata
from tracking.behavioral_events be;

comment on view tracking.v_behavioral_timeline is
'Tracking behavioral timeline. Raw IP hashes are intentionally excluded. Default retention policy: 180 days, subject to approved deployment policy.';

comment on table tracking.behavioral_events is
'Behavioral evidence. Default retention target is 180 days; deletion is an Operations-scheduled maintenance concern.';

comment on table tracking.link_events is
'Link interaction evidence. Default retention target is 180 days; deletion is an Operations-scheduled maintenance concern.';

comment on table tracking.sessions is
'Behavioral session state. Default retention target is 180 days after last_seen_at; deletion is an Operations-scheduled maintenance concern.';


-- Approved cleanup primitive. Operations schedules execution; Tracking owns
-- the retention predicate and keeps the retention policy centralized.
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

-- Deterministic retention test hook: callers can execute the function inside a
-- transaction and roll back after verifying row counts in integration tests.
