# SentinelLayer Growth Systems — Master System Contracts

**Status:** Architecture baseline  
**Purpose:** Define boundaries, contracts, dependencies, and lifecycle between the ten production systems.  
**Principle:** Strategy evolves; execution contracts remain stable.

## 1. System map

1. Account Intelligence
2. Decision-Maker Intelligence
3. Buying-Intent / Research
4. Deliverability & Mail Infrastructure
5. Campaign & Message
6. Tracking & Behavioral Intelligence
7. Reply & Conversation Intelligence
8. Sales Execution / Human Handoff
9. Analytics & Learning
10. Operations & Control Plane

Cross-cutting foundations:
- Supabase/PostgreSQL — canonical durable state
- Python engine — deterministic execution
- Hermes — bounded AI analysis/generation
- n8n — thin integration/notification edge
- GitHub/CI — source control and delivery

## 2. Architectural rules

### Single source of truth
Supabase/PostgreSQL is the authoritative durable store for campaign, lead, event, state, and audit data. Derived dashboards/caches must be rebuildable.

### Deterministic execution
Scheduling, eligibility, suppression, state transitions, retries, idempotency, leases, and safety gates are deterministic. AI does not directly authorize unsafe or policy-sensitive sends.

### AI boundaries
Hermes may classify, extract, generate variants, summarize, and recommend. Consequential actions pass deterministic validation and policy gates.

### Version everything that changes
Campaign strategy, offers, messaging, CTAs, sequences, prompts, personalization policies, and experiments are immutable versions. New strategy means a new version; history remains attributable.

### Event history
Important observations are retained as events. Current state is materialized from validated events and explicit state transitions where practical.

### Fail closed
Ambiguous delivery, invalid configuration, suppression conflicts, missing policy, and critical infrastructure errors prevent unsafe duplicate or unintended sends.

## 3. System contracts

### 3.1 Account Intelligence
Purpose: build and maintain account-level facts and qualification.

Consumes source data, enrichment, and research inputs.

Produces canonical account identity, firmographics, technology/context facts, qualification evidence, and freshness metadata.

Does not own outbound scheduling, message generation, or sales opportunity state.

### 3.2 Decision-Maker Intelligence
Purpose: identify and qualify people relevant to an account.

Consumes account records and research evidence.

Produces person identity, role, decision authority/influence, contactability, evidence, and confidence.

Does not own campaign strategy or send state.

### 3.3 Buying-Intent / Research
Purpose: determine why and when an account/person may be commercially relevant.

Consumes account/person facts, external research, and observed signals.

Produces intent classification, evidence, confidence, freshness, and routing recommendation.

Intent is evidence-backed and time-sensitive, not permanent lead metadata.

### 3.4 Deliverability & Mail Infrastructure
Purpose: safely execute outbound mail.

Existing implementation contract includes:
- Supabase/PostgreSQL integration
- durable send state
- queue claiming
- worker leases/reclaim
- idempotency protections
- retry classification
- ambiguous-delivery handling
- SMTP provider abstraction
- Hostinger SMTP submission path
- configuration validation
- production entrypoint
- graceful shutdown
- Docker
- unit/integration/concurrency tests
- GitHub Actions CI

Consumes an eligible, rendered send request plus mailbox/provider policy.

Produces durable send attempt/result, provider Message-ID where available, status/failure classification, timestamps, and operational events.

Must enforce suppression, reply-stop, campaign/mailbox pause, limits, windows, idempotency, and kill switches.

### 3.5 Campaign & Message
Purpose: decide what should be communicated and under which strategy.

Consumes ICP/account/person/intent context, active strategy versions, experiments, assets, and prior-conversation constraints.

Produces an immutable/versioned treatment:
- strategy version
- offer version
- message/angle version
- CTA version
- sequence version
- personalization inputs/output
- selected assets
- experiment assignment

The execution engine consumes this contract; business strategy is not hard-coded into the mail engine.

### 3.6 Tracking & Behavioral Intelligence
Purpose: collect and interpret post-send, content, web, and product observations.

Events may include:
- send/acceptance
- bounce/deferral
- link click
- Loom interaction
- first-party brief page view
- page progression
- CTA interaction
- pricing/docs/product events

Email opens are weak/noisy evidence. Automated scanners/security systems can generate activity.

Produces normalized events, identity/account attribution, confidence, behavioral timeline, and signals consumed by intent and analytics.

### 3.7 Reply & Conversation Intelligence
Purpose: convert inbound messages into safe conversation state.

Consumes inbound mail, thread headers, send history, behavioral context, and suppression state.

Produces normalized reply, thread association, classification, extracted intent, commitments/promises, recommended next action, and conversation state.

Unsubscribe/complaint/wrong-recipient and equivalent suppression consequences are deterministic policy decisions, not merely AI recommendations.

### 3.8 Sales Execution / Human Handoff
Purpose: turn qualified engagement into human sales work and revenue progression.

Consumes conversation state, account/person context, intent evidence, campaign/message history, and behavioral timeline.

Produces sales tasks, handoff packages, meeting state, qualification data, opportunity state, outcomes, and revenue attribution.

A handoff contains enough context that the salesperson does not need to reconstruct the interaction manually.

### 3.9 Analytics & Learning
Purpose: measure the funnel and learn which strategies produce qualified pipeline/revenue.

Consumes durable events and business outcomes from all systems.

Produces operational metrics, funnel metrics, experiment results, attribution, cohort analysis, and strategy recommendations.

Analytics observes and recommends; it does not silently deploy a new strategy.

### 3.10 Operations & Control Plane
Purpose: govern system health, security, deployment, and emergency controls.

Owns configuration, secret references, feature flags, permissions, audit logs, health checks, metrics/logging, alerts, backups/recovery, migrations, deployment/rollback, campaign/mailbox/global pause, kill switches, and incident handling.

It governs all systems but does not absorb their domain logic.

## 4. Canonical execution contract

```
lead/person eligible
  -> campaign enrollment
  -> sequence treatment selected
  -> message rendered
  -> deterministic policy validation
  -> queued send
  -> atomic claim
  -> provider attempt
  -> accepted / failed / ambiguous
  -> durable result
  -> event emission
  -> behavioral/reply processing
```

No system may bypass the policy gate to send directly.

## 5. Canonical event envelope

Every significant event should be attributable to:

```
event_id
event_type
occurred_at
source_system
environment
account_id (when known)
person_id (when known)
lead_id (when applicable)
campaign_id (when applicable)
send_id (when applicable)
correlation_id
causation_id (when applicable)
schema_version
confidence (when interpretive)
payload
```

Do not put secrets or unnecessary personal data into event payloads.

## 6. State ownership

- Account Intelligence owns account research state.
- Decision-Maker Intelligence owns person qualification state.
- Intent owns current intent assessment and evidence.
- Campaign owns enrollment/treatment selection.
- Mail infrastructure owns send execution state.
- Tracking owns normalized behavioral observations.
- Conversation Intelligence owns conversation classification/state.
- Sales owns opportunity/revenue state.
- Analytics owns derived metrics, not source-of-truth business state.
- Operations owns system/configuration/incident state.

A system may read another system's state but must not silently mutate another system's domain state.

## 7. Versioning model

Versioned entities follow:

```
draft -> reviewed -> testing -> active -> retired
```

Historical records retain the exact versions used at execution time.

Example:

```
Strategy v3
Offer v2
Message v7
CTA v4
Sequence v5
Experiment E12 / Variant B
```

This makes revenue attribution reproducible.

## 8. Lead lifecycle

```
discovered
  -> qualified
  -> researched
  -> eligible
  -> enrolled
  -> contacted
  -> engaged
  -> replied
  -> qualified_sales
  -> meeting
  -> opportunity
  -> won / lost
```

Safety/terminal branches may include:

```
suppressed
bounced
unsubscribed
wrong_person
not_now
disqualified
```

Implementation may use separate orthogonal state machines rather than one overloaded status.

## 9. Campaign lifecycle

```
draft
  -> reviewed
  -> test
  -> active
  -> paused
  -> resumed
  -> retired
```

Activation requires configuration validation and operational safety checks.

## 10. Reply lifecycle

```
received
  -> normalized
  -> thread_matched
  -> classified
  -> action_selected
  -> human_handled / approved_automation
  -> resolved
```

Positive replies stop future cold-sequence sends unless an explicit sales policy says otherwise.

## 11. Tracking architecture

Default cold-email posture should minimize tracking.

Use tracking selectively for intentional assets:

```
cold email
  -> transparent first-party asset URL
  -> asset application
  -> event collection
  -> identity resolution
  -> confidence scoring
  -> intent/analytics
```

Do not equate an email open with a human read, a URL hit with human intent, or a scanner request with engagement.

Use opaque identifiers rather than exposing email addresses in URLs.

## 12. Hermes contract

Hermes may:
- classify replies
- extract structured intent
- generate personalization
- generate message variants
- draft suggested responses
- summarize analytics
- propose strategy hypotheses

Hermes should return schema-validated structured outputs where machine consumption is required.

Hermes must not independently:
- bypass suppression
- activate campaigns
- override sending limits
- resolve ambiguous delivery as successful
- delete audit history
- send without the execution/policy layer

## 13. Python engine contract

Python owns deterministic orchestration:
- scheduling
- eligibility
- queueing
- claiming
- leases
- retries
- state transitions
- policy enforcement
- provider integration
- event processing
- recovery

Business strategy remains data/configuration rather than hard-coded branching.

## 14. n8n contract

n8n remains a thin edge/integration layer.

Appropriate uses:
- imports/webhooks
- Slack/email alerts
- scheduled reporting
- external integration triggers
- manual control surfaces

Do not place core campaign state machines, send eligibility, retry logic, suppression logic, or transactional sequencing in n8n.

## 15. Failure propagation

### Provider failure
```
SMTP failure
 -> classify
 -> retry if safe
 -> dead-letter if exhausted
 -> operational alert
```

### Ambiguous delivery
```
unknown provider outcome
 -> ambiguous state
 -> no unsafe immediate resend
 -> reconciliation/recovery policy
```

### Bounce spike
```
events
 -> health detection
 -> operations policy
 -> mailbox/campaign throttling or pause
 -> human alert
```

### AI failure
```
invalid/timeout/low-confidence AI result
 -> deterministic fallback
 -> human review where necessary
 -> no unsafe state transition
```

## 16. Idempotency

Every externally consequential operation requires a stable idempotency key.

At minimum:
- send creation
- send claim
- provider attempt where supported
- inbound event ingestion
- tracking event ingestion
- reply ingestion
- state transition commands

A retry must not create a duplicate business effect.

## 17. Security boundaries

Production secrets must never be committed to Git.

Supabase RLS is an authorization boundary; application-level policy remains required.

Sensitive data should be minimized, encrypted where appropriate, access-controlled, and retained only as justified.

Audit records capture who/what changed critical configuration or state.

## 18. Environment separation

Minimum environments:

```
development
  -> local/mock providers

staging
  -> synthetic/test identities and controlled integrations

production
  -> real domains/mailboxes/provider credentials
```

Real outbound sending requires an explicit production configuration gate.

## 19. End-to-end: one lead to revenue

```
Account discovered
  -> account qualification
  -> decision-maker identified
  -> intent researched
  -> eligible campaign selected
  -> strategy/offer/message versions selected
  -> personalization generated/cached
  -> send queued
  -> deliverability engine executes
  -> behavioral/reply events collected
  -> intent updated
  -> reply classified
  -> sales handoff
  -> meeting
  -> opportunity
  -> won/lost
  -> revenue attribution
  -> analytics
  -> learning hypothesis
  -> future strategy version
```

## 20. Production gate

Do not activate real sending infrastructure until:
- database migrations are reproducible
- RLS/security is reviewed
- unit tests are green
- integration tests are green
- concurrency tests are green
- send idempotency is tested
- ambiguous delivery is tested
- suppression is tested
- reply-stop is tested
- campaign pause is tested
- global kill switch is tested
- retry/dead-letter behavior is tested
- observability is verified
- backup/restore is tested
- staging synthetic campaign is completed
- rollback is documented

Then:

```
buy domain
 -> configure DNS/authentication
 -> create mailboxes
 -> verify provider limits/policies
 -> warm infrastructure
 -> controlled production ramp
 -> monitor
```

## 21. What this contract does not freeze

It deliberately does not freeze:
- campaign strategy
- offer
- CTA
- sequence
- CRM product
- AI model
- mail provider

Those are replaceable implementations behind stable contracts.

## 22. Immediate implementation priority

Given that the mail-infrastructure subsystem is already substantially implemented, integration work should come before rebuilding it:

1. Freeze the mail-engine interface.
2. Define canonical campaign/message inputs.
3. Define event schemas.
4. Define tracking-to-intent interfaces.
5. Define reply-to-conversation interfaces.
6. Define sales handoff payload.
7. Define analytics attribution keys.
8. Add cross-system integration tests.
9. Add production control-plane gates.
10. Run an end-to-end synthetic lead through every state before real sending.

**Architecture principle:** keep the execution engine stable while allowing strategy, offers, messaging, CTAs, experiments, and AI behavior to evolve through versioned data/configuration.
