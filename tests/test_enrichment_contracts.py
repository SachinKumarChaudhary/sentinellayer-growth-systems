import pytest
from pydantic import ValidationError

from sentinellayer_growth_engine.enrichment_contracts import EnrichmentBatch


def test_enrichment_batch_accepts_one_to_three_unique_companies() -> None:
    batch = EnrichmentBatch.model_validate(
        {
            "packets": [
                {"company_id": 1, "domain": "one.example"},
                {"company_id": 2, "domain": "two.example"},
            ]
        }
    )
    assert [packet.company_id for packet in batch.packets] == [1, 2]


def test_enrichment_batch_rejects_more_than_three_companies() -> None:
    with pytest.raises(ValidationError):
        EnrichmentBatch.model_validate(
            {
                "packets": [
                    {"company_id": 1, "domain": "a.example"},
                    {"company_id": 2, "domain": "b.example"},
                    {"company_id": 3, "domain": "c.example"},
                    {"company_id": 4, "domain": "d.example"},
                ]
            }
        )


def test_research_agent_cannot_claim_verification() -> None:
    with pytest.raises(ValidationError):
        EnrichmentBatch.model_validate(
            {
                "packets": [
                    {
                        "company_id": 1,
                        "domain": "a.example",
                        "decision_makers": [
                            {
                                "full_name": "Jane Doe",
                                "contacts": [
                                    {
                                        "channel": "email",
                                        "value": "jane@a.example",
                                        "normalized_value": "jane@a.example",
                                        "verification_status": "verified",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        )


def test_duplicate_company_ids_are_rejected() -> None:
    with pytest.raises(ValidationError):
        EnrichmentBatch.model_validate(
            {
                "packets": [
                    {"company_id": 1, "domain": "a.example"},
                    {"company_id": 1, "domain": "a.example"},
                ]
            }
        )


def test_self_written_not_found_label_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EnrichmentBatch.model_validate(
            {
                "packets": [
                    {
                        "company_id": 1,
                        "domain": "a.example",
                        "personalization_angle": "NOT_FOUND — use generic hook",
                    }
                ]
            }
        )
