# Tracking Replay & Idempotency Contract

**Status:** Accepted — public GET semantics finalized; Platform/Campaign/Mail compatibility review passed.

## 1. Core rule

A repeated HTTP GET for the same tracking URL is **not inherently a duplicate business event**.

A person can legitimately click the same link multiple times. Security scanners can also request it multiple times. Therefore Tracking MUST NOT deduplicate ordinary GET observations using token, timestamp, correlation ID, IP hash, or user-agent.

## 2. Two different cases

### A. Ordinary observation

`GET /t/<opaque-token>` without a producer-supplied idempotency identity:

- record each valid observation;
- classify traffic conservatively;
- resolve identity only from the server-side token;
- do not manufacture an idempotency key;
- repeated observations remain separate evidence.

### B. Semantic retry

A trusted producer may provide a stable idempotency identity when it knows that repeated delivery represents the **same logical event**.

The identity MUST be stable across retries and scoped to the event producer/type. Tracking may persist it as `source_event_id` or `ingest_key`, subject to the database uniqueness constraint.

A semantic retry MUST NOT be used merely because two requests look similar.

No trusted producer idempotency boundary exists in the current Tracking public HTTP interface; implementing one is a separate future interface decision.

## 3. HTTP boundary

`X-Idempotency-Key` MUST NOT be accepted as a trusted idempotency mechanism on the public tracking GET endpoint.

A future authenticated/internal ingestion boundary MAY accept a producer-supplied idempotency key. Until that boundary exists, public GET requests are always independent observations.

Tracking must:

- never trust public client input to collapse behavioral observations;
- never use a client-provided key for person/account/campaign identity;
- preserve ordinary GET observations, including repeated requests;
- scope any future trusted idempotency key to an authenticated producer/event contract.

## 4. Security properties

Malformed tokens fail closed.

Destination URLs must be HTTPS.

Client-provided identity fields MUST NOT override identity resolved from the opaque token.

Automation classification is evidence, not proof of human identity.

## 5. Downstream interpretation

Tracking emits observations. Intent/Conversation/Analytics determine their commercial significance.

Examples:

- 5 scanner requests ≠ 5 human engagements.
- 5 legitimate repeated clicks are still 5 observations unless a trusted producer explicitly identifies them as retries.
- One click ≠ high buying intent.

## 6. Compatibility requirements

Platform MUST preserve these semantics in the canonical event contract.

Campaign/Mail MUST NOT assume that every tracking GET is idempotent.

Operations MUST preserve the tracking endpoint's ability to receive repeated observations and must not add infrastructure-level deduplication that changes these semantics.

## 7. Acceptance tests

1. Same token, no idempotency key, two requests → two observations. ✅ covered by application semantics; durable integration test remains a cross-system gate.
2. Public `X-Idempotency-Key` cannot affect public GET deduplication. ✅ regression-tested.
3. Different ordinary GET requests remain independent observations. ✅.
4. Malformed token → no identity-bearing event. ✅ regression-tested.
5. Scanner classification remains automated/unknown and never becomes definitive human identity. ✅ regression-tested.
6. Trusted producer idempotency is explicitly reserved for a future authenticated/internal interface; no public endpoint claims this capability. ✅.
