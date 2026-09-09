import pytest

from sentinellayer_growth_engine.tinyfish_batch import TinyFishRefreshEnricher


def test_refresh_limit_contract_rejects_more_than_twenty() -> None:
    with pytest.raises(ValueError, match="refresh limit"):
        TinyFishRefreshEnricher(None, None, None).run_refresh(limit=21)  # type: ignore[arg-type]
