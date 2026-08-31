# Campaign & Messaging Implementation Plan

## Objective
Build a versioned strategy layer that can evolve without changing the deterministic mail engine.

## Phase 1 — Data foundation

Implemented in Supabase:
- campaign_strategies
- strategy_versions
- offer_versions
- message_versions
- cta_versions
- sequence_versions
- versioned fields on sequence_steps
- experiments
- experiment_variants
- campaign_enrollments
- campaign version references
- campaign validation function

## Phase 2 — Resolver

Build a deterministic campaign treatment resolver:

```text
person + account + current priority + campaign
        |
        v
active strategy version
        |
        +--> offer version
        +--> sequence version
        +--> experiment assignment
        |
        v
step
        |
        +--> message version
        +--> CTA version
        +--> asset policy
        |
        v
render request
```

The resolver must return stable version identifiers and must not send mail.

## Phase 3 — Experiment assignment

Use a stable assignment key, preferably campaign_id + person_id, to avoid a lead moving between variants on every worker invocation.

Rules:
- assignment happens once per enrollment
- assignment is persisted
- allocation percentages are validated
- inactive/cancelled experiments cannot create new assignments
- historical assignments are immutable

## Phase 4 — Renderer

Inputs:
- message version
- CTA version
- enrollment context
- verified personalization values

Validation:
- no unresolved variables
- required evidence exists
- no unsupported claims
- asset policy satisfied
- target recipient unchanged

Output:
- rendered subject
- rendered body
- headers/metadata required by the mail engine
- exact strategy/offer/message/CTA/sequence/experiment IDs

## Phase 5 — QA gates

Draft → automated validation → human review → testing → active.

Active versions must not be edited in place.

## Phase 6 — Integration with existing mail engine

The existing engine already owns durable sends, queue claiming, worker leases/reclaim, idempotency, retries, ambiguous-delivery handling, SMTP abstraction, and production controls.

Integration point:

```text
Campaign/Message Resolver
        |
        v
RenderedSendTreatment
        |
        v
existing Send Engine
```

The campaign system must never bypass the existing execution gate.

## Phase 7 — Required tests

### Versioning
- old campaign remains attributable after a new strategy activates
- retired versions cannot be selected for new enrollments
- existing enrollments retain frozen version identifiers

### Rendering
- missing variable is rejected
- missing evidence is rejected
- invalid asset policy is rejected
- approved message renders deterministically

### Experiments
- stable assignment is repeatable
- allocation is within declared bounds
- one person has one variant per experiment/campaign enrollment

### Routing
- P1/P2/P3 choose configured treatments
- P4 is not enrolled unless explicitly configured
- negative/terminal state blocks enrollment

### Regression
- no changes to mail-engine idempotency
- no changes to suppression semantics
- no changes to provider retry semantics

## Phase 8 — Definition of done

A campaign can be created, reviewed, tested, activated, and enrolled without hard-coded copy or strategy in Python. Each resulting send can be traced back to the exact strategy, offer, message, CTA, sequence, and experiment versions used.
