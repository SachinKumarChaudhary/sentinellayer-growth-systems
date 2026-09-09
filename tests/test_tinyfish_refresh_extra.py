def test_refresh_result_contract_is_stable():
    from sentinellayer_growth_engine.tinyfish_batch import TinyFishRefreshRunResult

    result = TinyFishRefreshRunResult(1, 1, 0, [1], [], 7)
    assert result.requested == 1
    assert result.min_age_days == 7
