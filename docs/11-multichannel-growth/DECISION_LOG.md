# Sentinel Layer — Multi-Channel Growth Decision Log

**Status:** Canonical  
**Date:** 2026-09-08  
**Rule:** These decisions reflect the current product direction. Do not reinterpret them later without an explicit new decision.

## Decisions

### Business objective
Primary objective: generate more meetings and sales through coordinated multi-channel outreach.

Current KPI: **meeting booked**.

Channels cooperate. The system is not designed as a channel-vs-channel competition.

### ICP root
The **company** is the ICP/root campaign object.

Decision makers are people associated with the company and are the actionable outreach identities.

### Multiple campaigns
A company may belong to several campaigns simultaneously and different campaigns may target different decision makers.

Monthly campaign containers are preferred once stable. Initial operation uses campaign batches/lists.

### Decision makers
Decision makers are stored inside the company relationship.

A company should normally have multiple researched decision makers, ranked using the decision-maker playbook and company context.

Decision-maker contact information belongs to the decision-maker record.

### Company contacts
Generic company-level contact methods are a separate category.

Examples: info@, hello@, support@, sales@, press@, main company phone.

### Suppression
An individual opt-out applies to the relevant contact/scope.

A CISO saying "do not contact me" does **not** automatically suppress every other decision maker at the company.

A company-wide opt-out suppresses the company.

Other cross-contact decisions require human review with AI assistance.

### Enrichment starting point
Start from the **1,200 companies already stored in Supabase**.

Do not depend on the old 485-company enriched dataset for the new canonical pipeline.

### Decision-maker enrichment
The enrichment system should also discover useful company and social information for outreach, not just names/titles.

Target contact surfaces may include email, phone, LinkedIn, Instagram, Reddit, X and other public profiles when available.

### Decision-maker playbook
The uploaded Decision Makers Playbook is the canonical business rule source for:
- which roles to hunt
- conditional role priority
- evidence requirements
- anti-personas
- decision-maker enrichment expectations

### Buying-intent playbook
The uploaded Buying Intent Classification v2.1 / Lead Classification Playbook is the canonical business rule source for:
- FIT
- INTENT
- behavior
- negative flags
- modifiers
- P1-P4 routing
- personalization hierarchy

### Intent
Intent is company-level intelligence.

Intent discovery should use:
- company/web research
- dated company events
- hiring/security signals
- compliance events
- competitor signals
- Reddit/web dark-funnel signals
- first-party behavior after tracking exists

Reddit/web monitoring can both enrich known companies and discover candidate companies.

### AI scoring
AI does not replace deterministic FIT/INTENT rules where the playbooks define explicit scoring.

AI can explain evidence, synthesize context and make recommendations.

### Social nurturing
Social content is **optional warming**.

It is a recommendation signal, not a prerequisite for direct messaging.

AI may recommend content topics based on buying-intent themes.

### Outreach
Email can be automated after human/operator approval of a personalized sequence.

LinkedIn, Instagram and Reddit use Composio where the connected integration exposes the required capability and access is appropriate.

Human/operator handles unavailable, paid, restricted or consequential actions.

### AI/operator boundary
AI:
- researches
- enriches
- recommends
- drafts
- prioritizes

Human/operator:
- approves sequences
- controls revenue-sensitive actions
- can stop/edit/re-route

System:
- persists state
- executes approved automation
- records outcomes
- enforces safety and suppression

### Hermes
Hermes is an operating agent and may access MCP/tooling/Composio.

Hermes is not the system of record.

### TinyFish
TinyFish Search + Fetch is the primary web research/enrichment mechanism.

Use it as much as useful **within actual rate limits**.

Cache results and avoid redundant re-fetches.

Do not use TinyFish as the default campaign-execution layer.

### AI web research
AI assistants/agents may research publicly available information to find company facts, decision makers, public emails, phones, social profiles and buying-intent evidence.

Do not assume any web agent is immune from rate limits, blocks or access restrictions.

### Apify
Apify is reserved primarily for **email finding/enrichment** in the current architecture.

Do not use it as the default general scraping system.

### Email verification
Free evidence/oracles come first.

QEV and Email Hippo are used after candidate reduction.

Candidate verification is progressive; do not verify every possible address.

### Free oracles
The existing free-oracle design remains valid and should run before paid spend.

MX/domain health should prevent wasted verification attempts on dead domains.

### Email provenance
Every candidate email should retain source/evidence and verification provenance.

A pattern-derived email is a candidate until verified.

### CTA links
A separate domain is **not currently required**.

Use the primary branded domain with a human-readable /go/ path initially.

Public social profiles/posts should avoid ugly opaque-looking links where a branded destination is preferable.

Opaque tokens remain the internal attribution mechanism.

### Public social tracking
Do not require person-level attribution for public social impressions when the platform does not legitimately expose identity.

Placement/content/campaign attribution is sufficient where exact person identity is unavailable.

### Attribution
The source of truth is the complete interaction journey.

Do not require one channel to receive exclusive credit.

Numerical first-touch/last-touch/multi-touch models are future reporting views, not the canonical event lineage.

### Tracking priorities
Primary behavioral evidence:
1. Conversations
2. CTA clicks
3. Meeting-page visits

Other engagement signals are supporting evidence.

### Conversation model
Track whether a conversation has started and follow-up state around contacts, while retaining the channel used for each touchpoint.

Cross-channel interaction history should be reconstructable.

### Follow-up
AI recommends the next action/channel.

Human/operator approves consequential actions.

### Calling
Automatic calling is future scope. Do not build it into the current MVP.

### Existing social content
Content is scheduled/published as a separate operational activity. AI may recommend content themes from buying intent.

### 1,200-company enrichment
The 1,200 companies should be enriched from scratch under the new canonical schema.

### Quality principle
Evidence and provenance are more important than filling every field.

Never fabricate a person, contact, URL, event or intent signal.

## Canonical documents

- `docs/11-multichannel-growth/CANONICAL_SYSTEM_DESIGN.md`
- `docs/11-multichannel-growth/ENRICHMENT_AND_INTENT_PIPELINE.md`
- `docs/11-multichannel-growth/OUTREACH_AND_OPERATOR_WORKFLOW.md`
- `docs/11-multichannel-growth/TRACKING_CTA_ATTRIBUTION.md`
- `docs/11-multichannel-growth/AI_AGENT_AND_TOOLING_CONTRACT.md`

## Source business playbooks

- Decision Makers Playbook
- Buying Intent Classification v2.1
- Lead Classification Playbook
- Enrichment & Deep Enrichment
- Free Oracles

## Explicitly unresolved implementation decisions

These remain open until separately decided:
- Exact Supabase table/column schema for the new entities.
- Exact Composio actions/scopes available to the connected accounts.
- Exact TinyFish rate-limit numbers and scheduling strategy based on live service limits.
- Exact QEV/Email Hippo/Apify interfaces and costs.
- Exact operator UI implementation.
- Exact Reddit RSS/source coverage and company-resolution method.
- Exact first-party `/go/` routing implementation.
- Exact cadence for recurring company intent refreshes.

**Rule:** Do not fill these gaps with assumptions. Inspect the actual integration/tool, then document the decision.
