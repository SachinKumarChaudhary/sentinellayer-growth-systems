from datetime import UTC, date, datetime
from uuid import uuid4

from sentinellayer_growth_engine.enrichment_contracts import (
    CompanyFacts,
    ContactMethod,
    DecisionMaker,
    EnrichmentPacket,
    Evidence,
    IntentSignal,
)
from sentinellayer_growth_engine.enrichment_repository import EnrichmentRepository


class FakeCursor:
    def __init__(self, rows: list[tuple] | None = None) -> None:
        self.executed: list[tuple[str, tuple]] = []
        self._rows = rows or []
        self.rowcount = 1
        self.description = None

    def execute(self, query: str, params: tuple = ()) -> None:
        self.executed.append((query, params))

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None


def _packet() -> EnrichmentPacket:
    return EnrichmentPacket(
        company_id=123,
        domain="example.com",
        company_facts=CompanyFacts(
            employee_count=120,
            monthly_sessions=250_000,
            has_login=True,
            vertical="commerce",
            ownership_type="independent",
            india_bridge=True,
            data_sensitivity="customer_accounts",
        ),
        decision_makers=[
            DecisionMaker(
                full_name="Jane Doe",
                title="CTO",
                role_family="engineering",
                role_priority=1,
                confidence=0.9,
                contacts=[
                    ContactMethod(
                        channel="email",
                        value="jane@example.com",
                        normalized_value="jane@example.com",
                        source="company_team_page",
                    )
                ],
            )
        ],
        intent_signals=[
            IntentSignal(
                signal_type="Funding round",
                signal_date=date(2026, 9, 1),
                weight=999,
                half_life_days=1,
                confidence=0.8,
            )
        ],
    )


def test_company_facts_are_persisted_to_canonical_table() -> None:
    cursor = FakeCursor()
    repository = EnrichmentRepository(lambda: None)  # type: ignore[arg-type]
    repository._upsert_company_facts(cursor, _packet(), datetime.now(UTC))

    query, params = cursor.executed[0]
    assert "intelligence.company_facts" in query
    assert params[:4] == (123, 120, 250_000, True)
    assert params[6] is True


def test_decision_maker_and_contact_upsert_use_canonical_relationship() -> None:
    decision_maker_id = uuid4()
    cursor = FakeCursor(rows=[(decision_maker_id,)])
    repository = EnrichmentRepository(lambda: None)  # type: ignore[arg-type]
    ids = repository._upsert_decision_makers(cursor, _packet(), datetime.now(UTC))

    assert ids["jane doe"] == decision_maker_id
    assert "growth.decision_makers" in cursor.executed[0][0]
    assert "growth.decision_maker_contact_methods" in cursor.executed[1][0]
    assert cursor.executed[1][1][0] == decision_maker_id


def test_intent_persistence_uses_canonical_weight_and_half_life() -> None:
    cursor = FakeCursor()
    repository = EnrichmentRepository(lambda: None)  # type: ignore[arg-type]
    repository._insert_intent_signals(cursor, _packet(), datetime.now(UTC))

    query, params = cursor.executed[0]
    assert "intelligence.intent_signals" in query
    assert params[1] == "funding"
    assert params[2] == date(2026, 9, 1)
    assert params[3] == 3
    assert params[4] == 21


def test_evidence_hash_is_stable_for_same_payload() -> None:
    evidence = Evidence(
        claim_type="funding",
        claim={"amount": "$5M", "date": "2026-09-01"},
        source_url="https://example.com/news",
        source_type="web",
    )
    payload = evidence.model_dump(mode="json")
    assert EnrichmentRepository._hash_evidence(payload) == EnrichmentRepository._hash_evidence(payload)
