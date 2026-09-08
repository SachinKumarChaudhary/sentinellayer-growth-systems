-- Forward security hardening for the existing decision-maker approval gate.
-- The approval function is SECURITY DEFINER and must remain backend-only.

revoke all on function growth.approve_decision_maker_review(uuid, text, text) from public;
revoke all on function growth.approve_decision_maker_review(uuid, text, text) from anon;
revoke all on function growth.approve_decision_maker_review(uuid, text, text) from authenticated;
grant execute on function growth.approve_decision_maker_review(uuid, text, text) to service_role;
