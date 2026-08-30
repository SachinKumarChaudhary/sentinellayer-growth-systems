# Concurrency test plan

The Python unit suite validates the application contract. Database concurrency must be proven against PostgreSQL/Supabase because a mocked cursor cannot prove row-lock semantics.

## Required integration assertions

1. Seed one queued send with a due timestamp.
2. Start two independent database connections and call `claim_due(1, worker)` concurrently.
3. Assert exactly one worker receives the send.
4. Assert the other worker receives zero rows.
5. Assert the send has one active claim and one incremented attempt.
6. Verify a worker restart does not make a claimed send permanently lost.
7. Verify a retry becomes claimable only at its persisted `next_attempt_at`.
8. Verify recording an accepted result is idempotent for the same `send_id`.
9. Verify a second logical send cannot be created from a retry of the same idempotency key.

## Production gate

Do not mark concurrency/idempotency complete from unit tests alone. These assertions must execute against the real Supabase/Postgres schema before production mailboxes are purchased.
