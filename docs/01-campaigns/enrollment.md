# Campaign Enrollment Service

Enrollment turns a validated eligible person into one durable campaign enrollment and freezes the treatment-version identifiers selected by the Campaign Resolver.

It does not send mail, claim delivery work, recompute ICP/FIT/intent, render content, or mutate existing enrollments.

## Safety invariants
1. Validate campaign configuration before enrollment.
2. Priority is P1-P4.
3. A decision-maker review must exist for the same campaign and person.
4. The review must be eligible, have at least one verified contact, and have explicit operator approval before enrollment.
5. CISO-suppressed decision makers cannot pass the review gate because ranking marks them ineligible.
6. The database trigger is the final enrollment gate; application ranking is never outreach approval.
7. The database unique constraint on campaign_id + person_id is the final concurrency/idempotency guard.
8. Repeating the same frozen treatment is idempotent.
9. A different treatment for an existing enrollment is a conflict.
10. Unknown database failures are not treated as success.
11. Existing enrollments retain frozen version identifiers.

## Flow
Enrichment -> DM ranking -> contact verification -> operator review -> Enrollment Service -> durable enrollment -> Sequence Orchestrator

Ranking only bounds the operator queue; it does not authorize outreach. Verification and explicit human approval are separate gates.

Real concurrency must be proven against Supabase/PostgreSQL, not an in-memory mock.
