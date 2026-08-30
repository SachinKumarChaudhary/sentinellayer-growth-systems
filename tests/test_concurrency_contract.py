from sentinellayer_growth_engine.db import Database


def test_claim_contract_requires_worker_identity() -> None:
    db = Database("postgresql://invalid")
    try:
        db.claim_due(batch_size=1, worker_id=" ")
    except ValueError as exc:
        assert "worker_id" in str(exc)
    else:
        raise AssertionError("blank worker identity must be rejected")


def test_claim_contract_has_bounded_batch() -> None:
    db = Database("postgresql://invalid")
    for size in (0, 501):
        try:
            db.claim_due(batch_size=size, worker_id="worker")
        except ValueError as exc:
            assert "batch_size" in str(exc)
        else:
            raise AssertionError("invalid batch size must be rejected")
