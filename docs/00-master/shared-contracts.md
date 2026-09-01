# Shared Contracts — Cross-System Machine Contracts

**Status:** v1 design contract
**Purpose:** Convert the existing ten-system architecture into explicit, machine-enforceable interfaces. These contracts complement `system-contracts.md`: the master contract defines ownership and guarantees; this document defines the data exchanged between systems.

## 1. Contract principles

- Stable IDs are opaque UUIDs or existing canonical IDs; systems do not invent parallel identifiers.
- Every contract has `schema_version`.
- Timestamps are ISO-8601 UTC.
- Interpretive outputs carry confidence/evidence where applicable.
- Strategy-bearing objects are versioned and immutable once active.
- Contracts describe facts and requested actions; they do not grant permission to bypass deterministic policy.
- Unknown data is represented explicitly; consumers must not infer missing facts as true.
- Backward-incompatible changes require a new schema version.

## 2. Canonical identifiers

| Entity | Canonical field | Owner |
|---|---|---|
| Account | `account_id` | Account Intelligence |
| Person | `person_id` | Decision-Maker Intelligence |
| Lead | `lead_id` | Lead/intelligence data layer |
| Campaign | `campaign_id` | Campaign system |
| Enrollment | `enrollment_id` | Campaign system |
| Strategy version | `strategy_version_id` | Campaign system |
| Offer version | `offer_version_id` | Campaign system |
| Message version | `message_version_id` | Campaign system |
| CTA version | `cta_version_id` | Campaign system |
| Sequence version | `sequence_version_id` | Campaign system |
| Sequence step | `sequence_step_id` | Campaign system |
| Experiment | `experiment_id` | Campaign system |
| Experiment variant | `experiment_variant_id` | Campaign system |
| Send | `send_id` | Mail engine |
| Provider attempt | `attempt_id` | Mail engine/provider layer |
| Provider message | `provider_message_id` | Mail provider |
| Reply | `reply_id` | Conversation system |
| Conversation | `conversation_id` | Conversation system |
| Event | `event_id` | Event-owning producer |
| Sales task | `sales_task_id` | Sales system |
| Opportunity | `opportunity_id` | Sales system |
| Meeting | `meeting_id` | Sales system |

Existing upstream identifiers must be preserved. Do not create `account_id` duplicates merely because a downstream system prefers a different key.

## 3. AccountRef

Minimum fields:
- `account_id`
- `domain`
- `account_name`
- `qualification_status`
- `source`

Optional:
- `employee_band`
- `traffic_band`
- `geography`
- `vertical`

Account intelligence owns the authoritative account record.

## 4. PersonRef

Minimum fields:
- `person_id`
- `account_id`
- `email`
- `name`
- `title`
- `contactability_status`

Optional:
- `linkedin_url`
- `buyer_role`
- `decision_authority`
- `verification_status`

Never overwrite verified identity with an AI guess.

## 5. IntentSnapshot

Represents the current output of the existing intent model at a point in time.

Required:
- `account_id`
- `person_id` when person-specific
- `fit_score`
- `intent_score`
- `priority`
- `negative_flags`
- `behavior_flags`
- `evidence[]`
- `calculated_at`
- `model_version`

The existing buying-intent model is the upstream authority. FIT is static, INTENT decays from dated signals, and behavior can override priority; the existing specification defines this separation. The campaign layer consumes its final priority rather than recomputing it. fileciteturn0file0L10-L16

## 6. CampaignEnrollment

Freezes the treatment context for one person in one campaign.

Required:
- `enrollment_id`
- `campaign_id`
- `person_id`
- `account_id`
- `priority_at_enrollment`
- `strategy_version_id`
- `offer_version_id`
- `sequence_version_id`
- `enrolled_at`
- `status`

Optional:
- `experiment_id`
- `experiment_variant_id`
- `message_context`
- `personalization_snapshot_id`

Once created, version references are immutable unless an explicit enrollment migration is recorded.

The campaign documentation explicitly requires exact treatment versions to be frozen at enrollment and historical sends to remain attributable. fileciteturn2file0

## 7. RenderedSendTreatment

This is the critical boundary between Campaign/Message and the existing Send Engine.

Required:
- `schema_version`
- `enrollment_id`
- `campaign_id`
- `person_id`
- `account_id`
- `sequence_step_id`
- `strategy_version_id`
- `offer_version_id`
- `message_version_id`
- `cta_version_id`
- `sequence_version_id`
- `recipient_email`
- `subject`
- `body_text`
- `headers`
- `rendered_at`

Optional:
- `experiment_id`
- `experiment_variant_id`
- `asset`
- `personalization`
- `reply_to`

Required behavior:
- complete and deterministic after rendering
- no unresolved placeholders
- no invented claims
- recipient identity fixed
- asset/link policy validated
- exact version identifiers retained

The campaign implementation specification defines the resolver → `RenderedSendTreatment` → existing send-engine interface and states the campaign layer must not send mail itself. fileciteturn3file0

## 8. SendRequest

The mail-engine request wrapper around a validated rendered treatment.

Required:
- `schema_version`
- `send_id`
- `idempotency_key`
- `campaign_id`
- `person_id`
- `sequence_step_id`
- `mailbox_id`
- `scheduled_at`
- `treatment`

The Send Engine may reject the request for policy/health/suppression reasons.

## 9. ProviderOutcome

Normalized provider result:

Required:
- `send_id`
- `attempt_id`
- `provider`
- `outcome_type`
- `occurred_at`

`outcome_type` values:
- `accepted`
- `temporary_failure`
- `permanent_failure`
- `ambiguous`
- `policy_rejection`
- `timeout`
- `connection_failure`

Optional:
- `provider_message_id`
- `smtp_code`
- `provider_status`
- `raw_reference`
- `retry_after`
- `error_code`
- `error_message`

Ambiguous outcomes must not be silently converted into a resend.

## 10. TrackingEvent

Every tracking event uses the canonical event envelope plus tracking fields.

Required:
- `event_id`
- `schema_version`
- `event_type`
- `occurred_at`
- `source_system`
- `environment`
- `account_id` when known
- `person_id` when known
- `campaign_id` when applicable
- `send_id` when applicable
- `correlation_id`
- `confidence`
- `payload`

Examples:
- `link_clicked`
- `loom_started`
- `loom_progress`
- `brief_viewed`
- `brief_page_progressed`
- `pricing_viewed`
- `docs_viewed`
- `diagnostic_completed`
- `trial_signup`

Email opens should remain low-confidence and should never be the sole trigger for a priority promotion.

## 11. ConversationHandoff

Produced by Reply & Conversation Intelligence for Sales.

Required:
- `conversation_id`
- `reply_id`
- `account_id`
- `person_id`
- `classification`
- `conversation_state`
- `source_send_id`
- `recommended_action`
- `created_at`

Optional:
- `intent_snapshot`
- `timeline`
- `commitments`
- `objections`
- `questions`
- `evidence`

For positive replies, the handoff should contain the exact outreach context and reply so the human does not reconstruct the thread manually.

## 12. SalesHandoff

Required:
- `sales_task_id`
- `account_id`
- `person_id`
- `trigger_type`
- `priority`
- `recommended_action`
- `created_at`

Required context:
- why-now evidence
- latest message/reply
- prior outreach summary
- relevant behavioral events
- campaign/strategy/offer versions
- suggested next step

## 13. AttributionContext

Every commercially meaningful action should retain:
- `account_id`
- `person_id`
- `campaign_id`
- `enrollment_id`
- `strategy_version_id`
- `offer_version_id`
- `message_version_id`
- `cta_version_id`
- `sequence_version_id`
- `experiment_id`
- `experiment_variant_id`
- `send_id` where applicable

This makes revenue attribution reproducible across changing strategies.

## 14. State transition ownership

Consumers request transitions; owners validate and perform them.

Examples:
- Campaign requests enrollment → Campaign system owns enrollment.
- Mail engine requests send claim → database/mail engine owns send state.
- Tracking emits behavior → Intent system owns intent calculation.
- Conversation classifies reply → Conversation system owns conversation state.
- Sales creates opportunity → Sales system owns opportunity state.

No cross-system direct table mutation should bypass the owning service/domain.

## 15. Compatibility policy

Compatible changes:
- add optional field
- add enum only when all consumers can tolerate it
- add optional metadata

Breaking changes:
- rename/remove required field
- change field semantics
- change enum meaning
- change identifier semantics

Breaking changes require a new schema version and migration strategy.

## 16. Contract test policy

Each boundary requires:
- valid payload test
- missing required field test
- invalid enum test
- wrong-owner mutation test
- version compatibility test
- idempotency test where side effects exist
- audit/event emission test

The full synthetic system test must prove:

`IntentSnapshot → CampaignEnrollment → RenderedSendTreatment → SendRequest → ProviderOutcome → TrackingEvent/Reply → ConversationHandoff → SalesHandoff → AttributionContext`.

## 17. Source-of-truth reminder

The existing ICP remains the authoritative definition of the target market, including customer/user login, valuable post-login sessions, 50–500 employees, and >=100K monthly combined sessions. fileciteturn0file2L23-L30

The decision-maker system remains the source for buyer identity and hierarchy; its playbook requires at least two relevant buyers when possible. fileciteturn0file1L14-L20

The existing campaign system owns strategy/offer/message/CTA/sequence versioning and explicitly does not own SMTP delivery or suppression enforcement. fileciteturn2file0

The mail engine remains the durable execution layer and should be integrated through the contracts above rather than rebuilt around campaign logic.
