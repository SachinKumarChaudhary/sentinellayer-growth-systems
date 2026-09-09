def test_refresh_contract_has_weekly_staleness_default():
    from sentinellayer_growth_engine.tinyfish_batch import TinyFishRefreshRunResult

    assert TinyFishRefreshRunResult(0, 0, 0, [], [], 7).min_age_days == 7
