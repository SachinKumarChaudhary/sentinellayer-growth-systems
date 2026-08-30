# Engine Reliability Contract

## Idempotency

A send has one stable internal `send_id` and one deterministic Message-ID. Retries of the same logical send must not create a second logical send record.

## Claiming

Workers must claim due sends atomically in the database. Application-side `SELECT` followed by a later update is not sufficient.

## Retry classification

Retry only transient transport failures. Permanent address failures, suppression, unsubscribe and policy failures are not retried.

## Backoff

Retries use bounded exponential backoff. The database stores the next eligible attempt time so a worker restart cannot lose retry state.

## Failure safety

If provider delivery succeeds but the worker crashes before recording success, the stable Message-ID and database idempotency key allow reconciliation rather than blindly creating another logical send.

## Concurrency

Multiple workers are expected. Tests must prove that a queued send can be claimed by at most one worker at a time.
