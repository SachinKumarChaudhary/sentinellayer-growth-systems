# Integration Contracts & Ownership Matrix

## Purpose

This document operationalizes `system-contracts.md` by defining who owns each cross-system object, what direction data moves, and which boundary must be tested.

## 1. Ownership matrix

| Contract | Producer | Consumer | Durable owner |
|---|---|---|---|
| AccountRef | Account Intelligence | all downstream | Account Intelligence/data layer |
| PersonRef | Decision-Maker Intelligence | all downstream | Decision-Maker Intelligence/data layer |
| IntentSnapshot | Intent/Research | Campaign, Sales, Analytics | Intent system |
| CampaignEnrollment | Campaign | Mail, Analytics | Campaign system |
| RenderedSendTreatment | Campaign/Renderer | Mail Engine | Campaign system |
| SendRequest | Campaign/Mail orchestration | Mail Engine | Mail Engine |
| ProviderOutcome | Provider adapter | Mail Engine, Analytics | Mail Engine |
| TrackingEvent | Tracking | Intent, Analytics | Tracking/event layer |
| ConversationHandoff | Conversation | Sales | Conversation system |
| SalesHandoff | Sales routing | Human operator/CRM later | Sales system |
| AttributionContext | all relevant systems | Analytics | Analytics projection; source IDs remain domain-owned |

## 2. Data direction

```text
Account → Person → Intent → Campaign → Mail
                         │                 │
                         │                 └→ ProviderOutcome
                         │                          │
                         └→ Tracking/Behavior ←────┘
                                   │
                                   ▼
                              Intent update

Mail → Reply → Conversation → Sales → Outcome → Analytics

All source events → Analytics/Learning
Operations/Control → all systems (governance only)
```

## 3. Boundary rules

### Intelligence → Campaign
Campaign consumes the final priority/routing output. It must not recompute FIT/INTENT or mutate upstream evidence.

### Campaign → Mail
Campaign provides `RenderedSendTreatment` / `SendRequest`. Mail decides whether sending is operationally safe and performs delivery. Campaign never talks directly to SMTP.

### Mail → Tracking
Mail emits durable transport events identified by `send_id`. Tracking may correlate them but must not alter send state.

### Tracking → Intent
Tracking emits observations with confidence. Intent decides whether observations affect buying-intent state according to the existing intent model.

### Mail → Conversation
Inbound messages are first persisted/associated. Conversation Intelligence interprets language and produces a handoff. Unsubscribe/suppression consequences remain deterministic.

### Conversation → Sales
Sales receives context-rich handoff, not just a classification.

### Sales → Analytics
Sales outcomes become the business truth for meetings, opportunities, won/lost and revenue.

## 4. Cross-system state transitions

Only the owning system may execute the authoritative transition.

Examples:
- campaign enrollment: Campaign owns
- send claim: Mail engine/DB owns
- mailbox pause: Operations/Mail owns according to the control model
- intent recalculation: Intent owns
- conversation classification: Conversation owns
- opportunity creation: Sales owns
- metric calculation: Analytics owns

Consumers may request transitions through typed service contracts.

## 5. Idempotency by boundary

### Campaign enrollment
Stable key: campaign + person + enrollment generation.

### Send
Stable key: campaign + person + sequence step.

### Provider event
Stable key: provider + external event ID where available; otherwise deterministic provider/message tuple.

### Tracking
Stable event ID from producer or a dedupe key based on source/session/event timestamp where explicitly defined.

### Reply
Use provider Message-ID as primary dedupe key when available.

### Sales handoff
Stable source event/conversation ID prevents duplicate tasks.

## 6. Security

- Never place provider secrets in contract payloads.
- URLs use opaque identifiers, not raw email addresses.
- PII is minimized in event payloads.
- Browser-facing APIs never receive worker/service-role credentials.
- Cross-system writes are authorized by the owning service.

## 7. Versioning

All machine-consumed schemas carry `schema_version`.

Backward-compatible additions may use the same major contract version when all consumers tolerate the field. Semantic/breaking changes require a new version.

## 8. Contract-test matrix

| Boundary | Required tests |
|---|---|
| Intent → Campaign | valid/invalid IntentSnapshot; P4 routing; negative flag handling |
| Campaign → Mail | RenderedSendTreatment validation; no unresolved variables; recipient integrity |
| Mail → Provider | accepted/temporary/permanent/ambiguous outcome normalization |
| Provider → Mail | duplicate event handling; ambiguous reconciliation |
| Mail → Tracking | send/event correlation |
| Tracking → Intent | confidence; identity; duplicate events; scoring integration |
| Mail → Conversation | thread matching; duplicate reply handling |
| Conversation → Sales | complete handoff; unsubscribe safety; positive-reply context |
| Sales → Analytics | attribution preservation; outcome uniqueness |

## 9. Full contract test

A synthetic fixture must travel through:

```text
AccountRef
→ PersonRef
→ IntentSnapshot
→ CampaignEnrollment
→ RenderedSendTreatment
→ SendRequest
→ ProviderOutcome
→ TrackingEvent / Reply
→ ConversationHandoff
→ SalesHandoff
→ AttributionContext
```

Assertions must verify that canonical IDs and attribution identifiers survive every boundary unchanged.

## 10. Implementation order

1. Add JSON/schema validation utilities.
2. Add contract fixtures.
3. Add producer-side validation.
4. Add consumer-side validation.
5. Add cross-system integration tests.
6. Add migration-safe schema version handling.
7. Run the full synthetic lifecycle in CI.

## 11. Non-goals

This contract layer does not freeze campaign strategy, offer, messaging, CTA, sequence, mail provider, CRM, or AI model. Those are versioned/replaceable behind these interfaces.
