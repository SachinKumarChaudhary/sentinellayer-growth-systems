# Campaign Enrollment Service

Enrollment turns a validated eligible person into one durable campaign enrollment and freezes the treatment-version identifiers selected by the Campaign Resolver.

It does not send mail, claim delivery work, recompute ICP/FIT/intent, render content, or mutate existing enrollments.

## Safety invariants
1. Validate campaign configuration before enrollment.
2. Priority is P1-P4.
3. The database unique constraint on campaign_id + person_id is the final concurrency/idempotency guard.
4. Repeating the same frozen treatment is idempotent.
5. A different treatment for an existing enrollment is a conflict.
6. Unknown database failures are not treated as success.
7. Existing enrollments retain frozen version identifiers.

## Flow
Eligibility -> Resolver -> Enrollment Service -> durable enrollment -> Sequence Orchestrator

Real concurrency must be proven against Supabase/PostgreSQL, not an in-memory mock.