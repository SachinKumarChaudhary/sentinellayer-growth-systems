from sentinellayer_growth_engine.tinyfish_batch import EnrichmentRepositoryPort


def test_repository_protocol_exposes_refresh_queue() -> None:
    assert "next_refresh_company_ids" in getattr(EnrichmentRepositoryPort, "__annotations__", {}) or hasattr(
        EnrichmentRepositoryPort, "next_refresh_company_ids"
    )
