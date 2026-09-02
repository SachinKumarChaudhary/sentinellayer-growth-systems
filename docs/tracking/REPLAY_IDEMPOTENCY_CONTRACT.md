# Tracking Replay & Idempotency Contract

**Status:** Proposed — Tracking-owned semantics; Platform/Campaign/Mail compatibility review required.

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

The identity MUST be stable across retries and scoped to the event producer/type. Tracking persists it as `source_event_id` or `ingest_key`, subject to the database uniqueness constraint.

A semantic retry MUST NOT be used merely because two requests look similar.

## 3. HTTP boundary

`X-Idempotency-Key` is optional.

Tracking must:

- bound the value length;
- never trust it for person/account/campaign identity;
- use it only for duplicate-effect protection;
- preserve ordinary GET observations when it is absent.

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

1. Same token, no idempotency key, two requests → two observations.
2. Same token, same trusted idempotency key → one logical persisted effect.
3. Different idempotency keys → independent observations.
4. Malformed token → no identity-bearing event.
5. Scanner classification remains automated/unknown and never becomes definitive human identity.
