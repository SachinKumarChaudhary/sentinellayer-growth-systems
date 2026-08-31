# Campaign & Messaging System

## Purpose

The Campaign & Messaging System converts existing account/person/intent intelligence into a controlled outreach treatment. It owns strategy, offer, message, CTA, sequence, personalization policy, assets, experiments, QA, and enrollment. It does not own SMTP delivery, suppression enforcement, or the deterministic mail worker.

## Inputs

The system consumes the existing:
- account/company identity and qualification
- decision-maker/person records
- FIT score
- decaying INTENT score
- behavior signals
- negative flags
- priority/routing output
- research evidence and freshness
- conversation constraints
- deliverability eligibility

The existing ICP defines a customer-facing login, valuable post-login sessions, the 50–500 employee band, and >=100K monthly web/app sessions as core qualifying conditions. The existing decision-maker playbook requires finding at least two relevant buyers when possible, with CISO/Security, CTO/Engineering, Founder/CEO, COO/CFOO, Legal, Product and Finance roles selected contextually. Those inputs are consumed; they are not recomputed here.

## Design principle: strategy is data, not code

Strategy changes with evidence and time. Never hard-code:
- P1 = one permanent campaign
- one permanent offer
- one permanent CTA
- one permanent five-step sequence
- one permanent personalization recipe

Instead, resolve an active version at campaign/enrollment time and persist the exact versions used.

Example treatment:

```text
P1 account
 -> strategy v3
 -> offer v2
 -> sequence v5
 -> step 3 message v7
 -> CTA v4
 -> experiment E12 / variant B
 -> personalization generated from evidence
```

Historical sends retain those identifiers for attribution and reproducibility.

## Version lifecycle

All strategy-bearing objects use:

```text
draft -> reviewed -> testing -> active -> retired
```

Never mutate an active version in place. Create a new version when the substance changes.

## Components

### 1. Strategy Registry

A strategy is the high-level GTM hypothesis.

Stores:
- stable strategy key
- name/description
- objective
- hypothesis
- target segment definition
- routing/treatment policy
- asset policy
- personalization policy
- evidence requirements
- experiment policy

A strategy may be reused by many campaigns, but each campaign freezes the selected strategy version.

### 2. Offer Registry

An offer is the reason the prospect should engage now.

Store versioned:
- promise
- desired outcome
- proof
- value/economics framing
- eligibility constraints
- implementation friction

The offer can change independently of the campaign shell.

### 3. Messaging Library

Messages are versioned by message key and angle.

Each message stores:
- subject template
- body template
- channel
- angle
- evidence requirements
- personalization policy
- QA status

The system should support multiple angles for the same strategy.

### 4. CTA Registry

CTA versions store:
- wording
- action type
- target
- friction score
- constraints

Default cold CTA should favor a low-friction reply when appropriate. A calendar link is not automatically the best CTA; the CTA must match the stage, offer and intended action.

### 5. Sequence Registry

A sequence is a versioned ordered treatment, not a permanent global rule.

A sequence contains steps. A step references:
- message version
- CTA version
- delay
- channel
- asset policy
- termination conditions

The current cold-email baseline may use five different angles/touches, but the system must permit 1–N steps and future sequence versions.

### 6. Personalization

Personalization follows evidence strength.

Preferred hierarchy from the existing buying-intent model:
1. named pain event
2. specific compliance trigger/deadline
3. physical-world/device consequence
4. community/drop/scalper harm
5. sensitive-data exposure
6. fresh capital/scale event
7. quantified VAMP/pain math
8. generic value proposition

Never invent company facts, vulnerabilities, customer names, financial figures or regulatory applicability.

Personalization generated for a lead/campaign is cached and versioned; later research can invalidate it and trigger regeneration.

### 7. Asset Routing

Assets are contextual escalation tools, not mandatory cold-email decorations.

Supported treatment types:
- no asset
- Loom
- first-party technical brief
- diagnostic/evaluation
- other approved content

Default:
- P1: may use personalized asset after strong contextual justification.
- P2: asset only when useful.
- P3: normally plain-text/lightweight treatment.

Do not stack multiple assets/trackers into every touch.

### 8. Experimentation

Experiments compare explicit variants under a declared hypothesis.

Each experiment stores:
- hypothesis
- success metric
- allocation method
- minimum sample size
- start/end dates
- status

A variant may select a strategy, offer and sequence version. The system must preserve the exact variant assigned to each enrollment.

Do not automatically promote a winner from tiny samples. Activation requires the defined approval workflow.

## Routing

Existing priority is the starting routing input:

```text
P1 -> highest-touch / strongest relevant treatment
P2 -> trigger-aware targeted treatment
P3 -> lightweight scalable treatment
P4 -> no active outreach / archive according to existing rules
```

Behavior overrides and negative caps are upstream business rules. This system consumes their final result.

## Campaign enrollment

Enrollment freezes the treatment context for a person:
- campaign
- strategy version
- offer version
- sequence version
- experiment variant
- enrollment timestamp
- current step
- next action
- termination status

Changing the active campaign strategy later must not silently mutate existing enrollments unless an explicit migration is performed.

## Sequence termination

Future automated steps stop on any configured terminal/interrupt condition, including:
- reply
- unsubscribe/suppression
- hard bounce
- manual cancellation
- account disqualification
- campaign pause
- mailbox/domain safety pause

Conversation safety belongs to the mail/reply systems, but campaign state must expose deterministic termination hooks.

## Message rendering

Rendering should be deterministic after personalization inputs are frozen.

Required validation before returning a message to the mail engine:
- all required variables resolved
- no unresolved placeholders
- recipient identity matches intended enrollment
- strategy/message/CTA versions are active or explicitly permitted for testing
- content length/policy checks pass
- links/assets follow the active asset policy
- no forbidden claims

The campaign system returns a complete treatment to the execution engine. It does not send mail itself.

## QA / approval

Recommended lifecycle:

```text
draft
 -> automated validation
 -> human QA
 -> testing
 -> controlled activation
```

Human QA checks evidence, claims, targeting, tone, offer/CTA consistency, and asset correctness.

## Strategy iteration loop

```text
strategy
 -> experiment
 -> sends / conversations / outcomes
 -> analytics
 -> hypothesis
 -> new version
 -> QA
 -> controlled test
 -> rollout / retirement
```

Analytics recommends. It does not silently rewrite active strategy.

## Required data relationships

```text
campaign_strategies
    -> strategy_versions

strategy_versions
    -> sequence_versions

offer_versions
message_versions
cta_versions
    -> sequence_steps

experiments
    -> experiment_variants

campaigns
    -> strategy_version
    -> offer_version
    -> sequence_version
    -> experiment

campaign_enrollments
    -> person
    -> exact strategy/offer/sequence versions
    -> experiment variant

sends
    -> exact sequence step
```

## Acceptance criteria

The subsystem is ready for integration when it can:
1. create versioned strategy/offer/message/CTA/sequence records;
2. validate and activate a campaign configuration;
3. assign a deterministic treatment to an eligible person;
4. freeze version identifiers at enrollment;
5. render a complete message without unresolved variables;
6. support experiments without losing attribution;
7. route P1/P2/P3 differently without duplicating core code;
8. terminate future steps deterministically;
9. preserve historical strategy versions;
10. hand a complete immutable send treatment to the mail engine.
