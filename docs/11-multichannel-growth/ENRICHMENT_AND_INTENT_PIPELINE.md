# Sentinel Layer — Enrichment and Buying-Intent Pipeline

**Status:** Canonical design baseline  
**Date:** 2026-09-08

## 1. Starting point

The system starts from the **1,200 companies already stored in Supabase**.

Do not depend on the old 485-company enriched dataset. Existing enrichment artifacts are historical/reference material only.

## 2. Pipeline

```
1,200 companies
  -> normalize/dedupe
  -> standard company enrichment
  -> company intelligence
  -> buying-intent research
  -> decision-maker planning
  -> decision-maker discovery
  -> contact/social enrichment
  -> email candidate verification
  -> evidence validation
  -> FIT + INTENT + priority
  -> campaign-ready
```

## 3. Tool responsibilities

### TinyFish

Primary web research/enrichment engine.

Use TinyFish Search + Fetch aggressively **within its rate limits**. Avoid unnecessary repetition through caching and research state.

TinyFish is not the bulk automation layer.

### AI research agents

AI assistants/agents are allowed to research publicly available information and structure evidence. They are useful for:

- Company research
- Decision-maker discovery
- Public contact discovery
- Buying-intent research
- Public social/profile discovery

Do not assume any AI/browser tool can bypass site restrictions. Respect public accessibility, provider limits, authentication boundaries and site policies.

### Apify

Use Apify specifically for **email finding/enrichment**, when useful.

Do not use Apify as the default general scraping layer.

### Free oracles

Run free/low-cost evidence first:

1. Public company-site evidence
2. Public source/ground-truth evidence
3. Domain pattern evidence
4. Mailbox existence signals
5. MX/domain health
6. Other corroboration

### Paid/free verification services

Use QEV and Email Hippo after cheaper checks have narrowed the candidate set.

Do not send every candidate through paid verification.

## 4. Email candidate pipeline

```
Person identified
  -> derive candidate email(s)
  -> domain/MX check
  -> public evidence/oracle checks
  -> choose strongest candidate
  -> QEV / Email Hippo as required
  -> final confidence + provenance
```

An email candidate is not automatically verified merely because it matches a company pattern.

Store:

- email
- candidate source
- evidence/source URL
- verification provider
- verification result
- verification timestamp
- confidence

## 5. Decision-maker discovery

The decision-maker playbook is the canonical rule set.

The research planner should inspect company characteristics first, then generate the roles to hunt.

Examples:

- CISO/Security exists -> prioritize CISO.
- No CISO -> CTO/VP Engineering is usually critical.
- <150 employees -> Founder/CEO is important.
- 150-500 employees -> COO/CFOO + CTO are important.
- Health/kids/age-gated -> include Legal.
- IoT -> include Product/IoT.
- Subscription/financial pain -> include Finance/Payments.

The company should normally receive at least two strong decision-maker candidates when evidence exists.

## 6. Decision-maker record

A decision maker should contain:

- name
- title
- company relationship
- email candidate(s)
- email verification state
- phone if available
- LinkedIn
- Instagram if available
- Reddit if available
- X/other social if available
- evidence
- confidence
- last verified/discovered timestamp

Generic company inboxes do not belong in the decision-maker email field.

## 7. Company-contact record

Separate from decision makers.

Examples:

- info@
- hello@
- support@
- sales@
- press@
- generic company phone
- public contact form

## 8. Evidence contract

Every factual enrichment claim should preserve:

- claim
- source URL
- source type
- observed_at
- event_date when applicable
- confidence

Prefer "not found" or empty over invented information.

Every cited source URL must actually support the claim.

## 9. Buying-intent signals

The canonical intent framework separates:

```
FIT = structural suitability
INTENT = dated/current buying window
BEHAVIOR = first-party engagement
NEGATIVES = suppression/caps
MODIFIERS = routing adjustments
```

Key intent categories include:

- Funding/scale events
- New executive hires
- Security/risk/fraud hiring
- Technology migration/replatform
- Competitor security-tool mentions
- Reddit/community dark-funnel complaints
- Seasonal windows
- Franchise/location launches
- New-market entry
- Compliance triggers

Signals must have a signal date when the event is dated.

## 10. Reddit/web dark-funnel pipeline

Known company:

```
Reddit/web signal
  -> company resolution
  -> intent_signal
  -> intent score recompute
```

Unknown company:

```
Reddit/web signal
  -> identify possible company
  -> ICP qualification
  -> company enrichment
  -> decision makers
  -> campaign candidate
```

A Reddit username does not need to be identified to make the company-level signal useful.

Do not infer identity from weak evidence such as username similarity alone.

## 11. Adaptive research depth

Do not deep-enrich every company every day.

Recommended behavior:

- High-priority/P1: deeper research.
- P2: moderate research and trigger watching.
- P3: lightweight enrichment.
- P4: minimal enrichment unless a new trigger appears.

Once a company is sufficiently enriched, recurring jobs should focus on new intent signals rather than repeating unchanged research.

## 12. Caching and rate-limit policy

Each research source should have:

- cache key
- fetched_at
- source URL
- research type
- last-success
- last-failure
- retry/cooldown state

Do not refetch unchanged URLs simply because another pipeline stage requests them.

## 13. Enrichment state machine

```
DISCOVERED
  -> COMPANY_ENRICHED
  -> INTENT_RESEARCHED
  -> DM_ROLES_SELECTED
  -> DECISION_MAKERS_FOUND
  -> CONTACTS_ENRICHED
  -> EMAILS_VERIFIED
  -> QUALITY_VALIDATED
  -> SCORED
  -> CAMPAIGN_READY
```

Ongoing intent monitoring continues independently after CAMPAIGN_READY.

## 14. Scoring

The newer v2 model is canonical:

- fit_score_v2
- intent_score_v2
- priority

Legacy score/tier values remain historical only.

Do not let an LLM invent the final score when deterministic playbook rules already exist.
