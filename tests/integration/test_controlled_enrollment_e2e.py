from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest


@pytest.mark.integration
def test_controlled_enrichment_verification_approval_enrollment_gate() -> None:
    """Exercise the consequential boundary without sending any outbound message."""
    dsn = os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        pytest.skip("SUPABASE_DATABASE_URL is required for integration tests")

    suffix = uuid4().hex
    company_id = int(uuid4().int % 2_000_000_000) + 1_000_000_000
    campaign_id = uuid4()
    decision_maker_id = uuid4()
    contact_method_id = uuid4()
    review_id = uuid4()
    enrollment_id = uuid4()
    email = f"e2e-{suffix}@example.invalid"

    try:
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            # Seed a disposable company and research output. No provider or outbound
            # transport is invoked by this test.
            cur.execute(
                "insert into public.companies (id, domain, name, source) values (%s,%s,%s,'controlled-e2e')",
                (company_id, f"e2e-{suffix}.invalid", "Sentinel Layer Controlled E2E"),
            )
            cur.execute(
                "insert into intelligence.company_facts (company_id, employee_count, monthly_sessions, has_login, vertical, ownership_type, india_bridge, data_sensitivity) values (%s,120,250000,true,'ecommerce','private',true,'high')",
                (company_id,),
            )
            cur.execute(
                "insert into intelligence.evidence (company_id, claim_type, claim, source_url, source_type, observed_at, event_date, confidence, evidence_hash) values (%s,'company_fact',%s::jsonb,'https://example.invalid/e2e','controlled_test',now(),current_date,1.0,%s)",
                (company_id, '{"fact":"controlled test evidence"}', f"e2e-{suffix}-evidence"),
            )
            cur.execute(
                "insert into intelligence.intent_signals (company_id, signal_type, signal_date, detected_at, weight, half_life_days, confidence, status) values (%s,'security_hiring',current_date,now(),3,14,1.0,'active')",
                (company_id,),
            )
            cur.execute(
                "insert into growth.decision_makers (decision_maker_id, company_id, full_name, title, role_family, role_priority, rationale, confidence) values (%s,%s,'Controlled E2E Security Lead','VP Security','security',1,'controlled evidence',1.0)",
                (decision_maker_id, company_id),
            )
            cur.execute(
                "insert into growth.decision_maker_contact_methods (contact_method_id, decision_maker_id, channel, value, normalized_value, source, source_url, verification_status, confidence) values (%s,%s,'email',%s,%s,'controlled_test','https://example.invalid/e2e','unknown',1.0)",
                (contact_method_id, decision_maker_id, email, email),
            )
            cur.execute(
                "insert into growth.campaigns (campaign_id, name, status) values (%s,'Controlled E2E Campaign','draft')",
                (campaign_id,),
            )
            cur.execute(
                "insert into growth.decision_maker_reviews (review_id, campaign_id, company_id, decision_maker_id) values (%s,%s,%s,%s)",
                (review_id, campaign_id, company_id, decision_maker_id),
            )

            # Verification is a provider-boundary state change, represented here by
            # the same canonical DB state that the verification repository writes.
            cur.execute(
                "update growth.decision_maker_contact_methods set verification_status='verified', verification_provider='controlled-test', last_verified_at=now() where contact_method_id=%s",
                (contact_method_id,),
            )

            # Approval is still required after verification.
            cur.execute(
                "select * from growth.approve_decision_maker_review(%s,%s,%s)",
                (review_id, "controlled-e2e-operator", "controlled integration test approval"),
            )
            approved = cur.fetchone()
            assert approved is not None
            assert approved[4] == "approved"

            cur.execute(
                "insert into growth.campaign_company_enrollments (enrollment_id, campaign_id, company_id, status, metadata, decision_maker_id, decision_maker_review_id) values (%s,%s,%s,'pending','{}'::jsonb,%s,%s)",
                (enrollment_id, campaign_id, company_id, decision_maker_id, review_id),
            )

            cur.execute(
                "select decision_maker_id, decision_maker_review_id, status from growth.campaign_company_enrollments where enrollment_id=%s",
                (enrollment_id,),
            )
            enrollment = cur.fetchone()
            assert enrollment == (decision_maker_id, review_id, "pending")

            # This E2E stops at enrollment by design: no campaign send, SMTP call,
            # or real recipient is involved. Attribution is exercised by the existing
            # tracking/conversation integration suites after a real provider event.
            conn.rollback()
    finally:
        # The transaction is rolled back above; this block is intentionally empty so
        # a failed assertion cannot accidentally issue destructive cleanup against
        # pre-existing production rows.
        pass
