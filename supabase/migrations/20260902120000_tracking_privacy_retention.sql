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
