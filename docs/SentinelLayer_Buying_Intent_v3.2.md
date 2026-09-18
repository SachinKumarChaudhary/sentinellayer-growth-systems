<callout icon="🔥" color="orange_bg">
	**Homepage placement:** Canonical buying-intent scoring, decay, validation, and routing system.
</callout>
# Status
**Canonical production system** for identifying, scoring, aging, validating, and routing reasons an ICP-fit account may buy Sentinel Layer now.
**Version:** 3.1  
**Campaign universe:** **1,200 Shopify leads**  
**Current mid-market cohort:** **485 leads with 50–500 employees**  
This document preserves the deeper buying-intent policies used in the research while separating three different layers:
1. **Main campaign model:** FIT × INTENT × BEHAVIOR → P1–P4
2. **Dark-funnel/community subsystem:** timing + pain + budget/mandate + reachability + stack for Reddit/community signals
3. **First-party product-qualified subsystem:** PQL/PQA behavior once Sentinel Layer has product/site telemetry
# 1. DEFINITION
> **Buying intent is the probability that an ICP-fit account has a sufficiently strong, sufficiently recent, and sufficiently credible reason to evaluate, purchase, or deploy Sentinel Layer now.**
Buying intent is **not**:
- company size
- traffic
- industry
- existence of a login
- sensitive data by itself
- Shopify usage
- generic regulation exposure
- executive seniority
- India affiliation
- generic technology presence
Those belong primarily to **ICP, Decision Makers, personalization context, or relationship routing**.
# 2. SIGNAL ≠ INTENT
A **signal** is an observable event or evidence point.
**Intent** is the interpretation that the signal makes the account more likely to buy now.
Examples:
- Shopify Plus present → technology context, not necessarily intent
- Replatforming to a new commerce/auth architecture → potential intent
- Funding round → budget capacity, not proof of security shopping
- Security engineer hired → stronger security buying signal
- Explicit company-specific ATO incident → strong pain signal
- SentinelLayer pricing/docs visit → first-party buying behavior
Never treat every interesting fact as intent.
# 3. THE CORE BUYING-INTENT MODEL
## Layer 1 — FIT
Owned by the ICP.
Question: **Does this company structurally have a SentinelLayer problem?**
## Layer 2 — INTENT
Owned by this document.
Question: **Is something making that problem more commercially actionable now?**
## Layer 3 — BEHAVIOR
Owned here and strongest once available.
Question: **Has the account or buyer actually interacted with Sentinel Layer?**
## Layer 4 — NEGATIVE / FRICTION
Question: **What could suppress purchase likelihood despite positive signals?**
Final routing:
> **Priority = f(ICP Fit, Intent, Behavior, Negative/Friction, routing modifiers)**
# 4. MASTER INTENT TAXONOMY
The research framework groups buying signals into six broad families:
1. **Organizational triggers** — funding, executive changes, acquisitions, expansion
2. **Technographic triggers** — replatforming, auth migration, security-stack changes
3. **Hiring signals** — security, fraud, risk, trust & safety hiring
4. **Web/behavioral signals** — docs, pricing, trial, product usage
5. **Topic/research intent** — explicit evaluation, searches, comparisons, security research
6. **Community/dark-funnel signals** — Reddit/forums/customer complaints/security discussions
A1–A6 are the operational enrichment buckets used to collect evidence across this taxonomy.
# 5. A1–A6 RESEARCH FRAMEWORK
Every lead retains all six fields. **Never leave A1–A6 blank.** When no evidence exists, record `none found` with the search context where useful.
## A1 — Security / Fraud / Takeover Pain
Research:
- account takeover
- compromised accounts
- payout/bank-account changes
- chargebacks
- fraud
- suspicious activity
- session abuse
- bot/scalper abuse
- community complaints
- public incidents
### Signal strength
**Very strong:** company-specific incident  
**Strong:** company-specific customer complaint/evidence  
**Moderate:** repeated company-specific abuse  
**Weak:** generic category discussion  
**None:** no relevant evidence
Each meaningful event should retain:
`signal_type | signal_date | source_url | source_evidence | confidence`
## A2 — Technology / Attack-Surface Change
Technology **presence** is mainly ICP/context.
Technology **change** can create intent.
Examples:
- commerce replatform
- authentication migration
- new customer portal
- new app
- account-flow redesign
- payment architecture change
- new administrative capability
- major security-stack change
Rule:
> **Technology exists = context. Technology is changing = potential intent.**
## A3 — Security / Compliance / Hiring
Search for:
- security engineer
- application security
- cloud security
- security architect
- fraud analyst
- risk analyst
- trust & safety
- security leader
- compliance/security programs
- enterprise security requirements
### Strong signals
- new CISO/security leader
- security/fraud team expansion
- security-specific hiring spike
- active security project
- enterprise vendor security review
- new actionable compliance project
### SOC 2 / ISO policy
**HAS SOC 2 / ISO 27001** is primarily an ICP/security-maturity signal.  
**NEEDS SOC 2 / active audit / enterprise security gate** is a buying-intent signal when the requirement is current and actionable.
Do not treat generic existence of a regulation or certification as automatic current intent.
## A4 — Competitor / Alternative Evaluation
Search for:
- Sift
- SEON
- Forter
- Kount
- Castle
- Arkose
- Signifyd
- DataDome
- other fraud/ATO/security vendors
### Evidence hierarchy
**Strong:** explicit tool comparison/evaluation or dissatisfaction  
**Moderate:** known incumbent usage indicating an existing budget/problem category  
**Weak:** incidental mention in a job description/article
Rule:
> **Existing competitor usage is not automatically high intent.** Investigate whether there is a gap, dissatisfaction, replacement project, or adjacent need.
## A5 — India / Relationship Signal
A5 is a **relationship, routing, and personalization modifier**, not intrinsic buying intent.
Possible evidence:
- Indian founder/entity
- Bengaluru engineering presence
- India business/entity connection
- India expansion/shipping
Use for:
- founder rapport
- timezone alignment
- relationship strength
- route selection
Do not score India affiliation as proof that the company is shopping for Sentinel Layer.
## A6 — Funding / Growth / Executive / Business Change
Capture:
- funding
- acquisition
- new CEO/CFO/CTO/CISO/CPO
- new market
- geographic expansion
- new store/location
- new product
- major growth milestone
- enterprise expansion
### Interpretation
**Funding:** budget capacity, not proof of security buying.  
**New relevant executive:** stronger when security, technology, risk, finance, or operations owned by the role.  
**Expansion:** stronger when it materially increases users, sessions, countries, regulatory exposure, payment volume, or device footprint.
# 6. SIGNAL QUALITY POLICY
Every meaningful signal must be represented with evidence.
### High confidence
- official company announcement
- official job posting
- official filing
- first-party product behavior
- company-authored page
- authoritative company-specific source
### Medium confidence
- reputable business publication
- reliable secondary database
- credible interview/profile
### Low confidence
- unsourced aggregation
- forum speculation
- indirect category evidence
**Low-confidence evidence should not create P1 alone.**
# 7. DATED-EVENT POLICY
Every dated event gets a `signal_date`.
Required when available:
`signal_type | signal_date | source_url | evidence | base_weight | half_life | confidence`
Never replace a known date with vague language such as `recently`.
The `signal_date` is mandatory because freshness drives intent decay.
# 8. INTENT DECAY
Use exponential freshness rather than binary active/inactive labels:
```plain text
freshness = 2 ^ (-days_since_signal / half_life)
signal_value = base_weight × freshness
```
This models the fact that a trigger gradually cools rather than becoming worthless overnight.
# 9. RECOMMENDED INTENT SIGNAL WINDOWS
<table header-row="true">
<tr>
<td>Signal</td>
<td>Weight</td>
<td>Half-life</td>
<td>Operational peak/action window</td>
</tr>
<tr>
<td>Trial / active evaluation</td>
<td>5</td>
<td>14d</td>
<td>Act immediately</td>
</tr>
<tr>
<td>SDK install / /evaluate activity</td>
<td>5</td>
<td>14d</td>
<td>Act immediately</td>
</tr>
<tr>
<td>Pricing/docs engagement</td>
<td>4</td>
<td>7d</td>
<td>\~24–72h strongest</td>
</tr>
<tr>
<td>Explicit company-specific incident</td>
<td>4</td>
<td>14d</td>
<td>Act rapidly</td>
</tr>
<tr>
<td>Competitor evaluation</td>
<td>3</td>
<td>30d</td>
<td>Act while evaluation is active</td>
</tr>
<tr>
<td>Security/fraud hiring</td>
<td>3</td>
<td>30d</td>
<td>While posting is live</td>
</tr>
<tr>
<td>New CISO/CTO/security leader</td>
<td>3</td>
<td>45d</td>
<td>First weeks/months</td>
</tr>
<tr>
<td>Security architecture/replatform</td>
<td>3</td>
<td>45d</td>
<td>During project window</td>
</tr>
<tr>
<td>New product/account capability</td>
<td>2</td>
<td>45d</td>
<td>Launch period</td>
</tr>
<tr>
<td>Funding ≥\$5M</td>
<td>3</td>
<td>21d</td>
<td>Early post-raise window</td>
</tr>
<tr>
<td>Major expansion/new market</td>
<td>2</td>
<td>60d</td>
<td>Before/during expansion</td>
</tr>
<tr>
<td>Executive/business event</td>
<td>2</td>
<td>45d</td>
<td>Transition window</td>
</tr>
<tr>
<td>Franchise/location expansion</td>
<td>2</td>
<td>60d</td>
<td>Launch window</td>
</tr>
<tr>
<td>Seasonal exposure</td>
<td>1</td>
<td>Event-based</td>
<td>Before peak demand</td>
</tr>
</table>
These windows are operating defaults; they are not evidence that every signal has identical real-world persistence.
# 10. COMPOUND-SIGNAL POLICY
One signal can mean **possible interest**.
Two genuinely independent recent categories can mean **active buying potential**.
Three or more independent categories can mean **high urgency**.
### Valid compound example
- security hiring
- new authenticated product capability
- company-specific fraud incident
### Invalid compound example
- Shopify Plus
- Klaviyo
- Cloudflare
Those are technology/context facts, not three independent intent signals.
# 11. INTENT SCORE
Calculate:
```plain text
raw_intent = Σ(weight × freshness)
intent_score = deterministic normalization(raw_intent → 0–10)
```
The implementation must expose the component contributions.
A human reviewer must be able to answer:
> **Why is this account an 8 rather than a 4?**
# 12. SCORE AUDITABILITY
Example:
```plain text
INTENT 8.1
├── Security hiring: 2.6
├── New CTO: 1.5
├── Replatform: 1.7
├── Funding: 0.8
└── First-party docs visit: 1.5
```
Do not expose a score without its evidence decomposition in the internal record.
# 13. FALSE-POSITIVE / SOLVED-PROBLEM POLICY
The system must distinguish a real active problem from historical or irrelevant discussion.
### Downgrade or reject evidence when:
- the article is merely a news link with no company-specific first-person evidence
- the problem has already been solved
- the incident concerns a consumer unrelated to the target company
- the discussion is academic/theoretical
- the lead is a closed duplicate
- the source is vendor-content engagement without evidence of company evaluation
- the event concerns licensing/billing rather than security/session risk
- the signal is too stale to represent current intent
### Solved-problem rule
If the evidence indicates the issue is resolved and no current follow-up window exists:
> **Downgrade to low/no current intent and do not spend deep enrichment effort solely on that event.**
The research/classifier may use an explicit solved/unsolved judgment, but the final production score must remain deterministic and auditable.
# 14. DARK-FUNNEL / COMMUNITY SUBSYSTEM
Community signals are valuable because buying research and pain discussions often occur outside vendor-controlled channels.
Primary sources:
- Reddit
- forums
- developer communities
- security communities
- public customer complaints
- public social discussions
The subsystem has two functions:
### Capture
Observe conversations/research already happening externally.
### Create
Publish/seed useful content in relevant communities so future interest has more observable surface area.
# 15. DARK-FUNNEL REDDIT SCORING MODEL
For Reddit/community-derived signals, retain the legacy 0–9 model as a **submodel**, not as the primary Shopify scoring system.
Five dimensions:
<table header-row="true">
<tr>
<td>Dimension</td>
<td>Max</td>
<td>Meaning</td>
</tr>
<tr>
<td>Timing / Trigger</td>
<td>2</td>
<td>freshness and strength of current event</td>
</tr>
<tr>
<td>Pain / Recurrence</td>
<td>2</td>
<td>severity and recurrence of the problem</td>
</tr>
<tr>
<td>Budget / Mandate</td>
<td>2</td>
<td>evidence of capacity or requirement to act</td>
</tr>
<tr>
<td>Reachability / Exclusivity</td>
<td>2</td>
<td>ability to reach the right buyer / useful unique signal</td>
</tr>
<tr>
<td>Stack Bonus</td>
<td>1</td>
<td>relevant compatible stack/platform bonus</td>
</tr>
</table>
### Legacy dark-funnel tiers
- **7–9:** A++ / HOT
- **5–6:** A / Warm
- **3–4:** B
- **0–2:** C
### Legacy SLA
- A++: respond rapidly, ideally same day
- A: follow up within the current outreach cycle
- B: nurture/watch
- C: suppress unless new evidence appears
### Compound promotion
If two independent dimensions/categories become strongly active, the lead may be promoted one tier **after quality checks**.
Do not use the dark-funnel 0–9 score as a replacement for the main FIT × INTENT × BEHAVIOR model.
# 16. PQL / PQA POLICY
Once first-party product telemetry exists, behavior becomes the strongest buying evidence.
### PQL candidates
- pricing interaction
- docs interaction
- trial signup
- active evaluation
- product usage
- `/evaluate` activity
- integration attempts
### PQA principle
Buying occurs at the **account level**, not merely the individual level.
Therefore:
> **PQA \> PQL** as a routing concept when multiple people from the same account show product engagement or actual usage indicates organizational evaluation.
A CTO visiting docs is useful. Multiple stakeholders from one company plus product usage is materially stronger.
# 17. FIRST-PARTY BEHAVIOR OVERRIDE
The strongest P1 candidates include:
- pricing-page engagement
- docs-page engagement
- trial signup
- SDK installation
- `/evaluate` activity
- demo request
- positive reply
- explicit information request
Behavior can force **P1**, but the behavior itself must be retained with timestamp and identity evidence where available.
# 18. BEHAVIOR RECENCY
First-party behavior also decays.
A docs visit today is stronger than a docs visit 30 days ago.
Recommended internal identity fields:
`company | person | email | LinkedIn identity | event timestamp | event type`
Identified CTO pricing engagement is stronger than anonymous traffic.
# 19. COMPLIANCE INTENT ENGINE
Compliance must be separated into four uses:
### FIT
Evergreen structural exposure.
### INTENT
Current deadline, active audit, new market entry, procurement gate, enforcement event, or regulated-product expansion.
### PERSONALIZATION
Use the specific rule/deadline that materially affects the account.
### NEGATIVE
The regulation does not meaningfully apply, the threshold is not met, or the evidence is stale/irrelevant.
# 20. COMPLIANCE SIGNAL MAP
<table header-row="true">
<tr>
<td>Framework / trigger</td>
<td>Primary role</td>
<td>Intent condition</td>
</tr>
<tr>
<td>PCI DSS 4.0</td>
<td>FIT/context</td>
<td>Current payment-security project, audit, or enforcement concern</td>
</tr>
<tr>
<td>California breach-notification requirements</td>
<td>FIT/context</td>
<td>CA exposure + current security/compliance work</td>
</tr>
<tr>
<td>GDPR Art. 32</td>
<td>FIT/context</td>
<td>New EU entry, active GDPR/security project, incident</td>
</tr>
<tr>
<td>FTC Click-to-Cancel / negative-option</td>
<td>FIT/context</td>
<td>Active subscription/compliance project or enforcement response</td>
</tr>
<tr>
<td>COPPA / minors</td>
<td>FIT</td>
<td>Current children-data security/compliance activity or relevant incident</td>
</tr>
<tr>
<td>DPDP India</td>
<td>FIT/context</td>
<td>India expansion, implementation project, enterprise requirement</td>
</tr>
<tr>
<td>HIPAA / health privacy</td>
<td>FIT</td>
<td>Current health-data security/compliance work or incident</td>
</tr>
<tr>
<td>SOC 2 / ISO 27001</td>
<td>Maturity/FIT</td>
<td>Active audit/procurement/security-gate project</td>
</tr>
<tr>
<td>New-market regulation</td>
<td>Intent</td>
<td>Entry into a new regime is current/forthcoming</td>
</tr>
<tr>
<td>Competitor enforcement event</td>
<td>Intent/context</td>
<td>Event prompts customer-side review or security initiative</td>
</tr>
<tr>
<td>Regulated-product launch</td>
<td>Intent</td>
<td>Product launch creates a new regulated session surface</td>
</tr>
</table>
Rule:
> **A law being on the books is not the same as a buying trigger.**
# 21. FUNDING POLICY
Funding creates potential budget capacity.
### Weak
Funding alone.
### Stronger
Funding + relevant executive change.
### Strongest
Funding + relevant executive change + security hiring/replatforming/problem evidence.
Do not write:
> `They raised money, therefore they need us.`
Write the actual observed event and its relevance.
# 22. EXECUTIVE-CHANGE POLICY
### Strong
- CISO
- CTO
- VP Engineering
- Head of Fraud/Risk
- security leader
### Moderate
- COO
- CFO/CFOO
- CPO
### Weak
- CMO
- Brand
- Marketing
The event is stronger when the newly appointed person owns a function connected to the session-security problem.
# 23. HIRING POLICY
Strong hiring signals include:
- security engineer
- application security
- cloud security
- security architect
- fraud analyst
- risk analyst
- trust & safety
- identity/access/security
- security leadership
Generic engineering hiring is **not** automatically security intent.
# 24. REPLATFORM / TECHNOLOGY-MIGRATION POLICY
A migration becomes intent when it reopens architecture decisions around:
- authentication
- customer accounts
- payments
- subscriptions
- backend architecture
- security stack
- account flows
Reason:
> security controls are easier to introduce while architecture is already changing.
# 25. PRODUCT-LAUNCH POLICY
A product launch becomes a meaningful intent signal when it changes the security surface:
- new connected device
- new customer portal
- new subscription capability
- new financial action
- new admin capability
- new account feature
- major authenticated product expansion
A normal SKU/color/marketing launch is not enough.
# 26. DARK-FUNNEL QUALITY POLICY
Use this hierarchy:
**company-specific incident**  
> repeated company-specific complaint
> credible category-specific abuse
> generic category discussion
Never use a generic Reddit complaint as evidence that the named company is experiencing the same problem.
# 27. NEGATIVE / FRICTION POLICIES
## Corporate-route-only
If the parent company centrally controls vendor/security procurement:
> **cap at P3 under the local-brand motion**
unless the route is changed to the true parent decision authority.
## M&A freeze
Recent acquisition/integration can suppress current purchasing activity.
Policy:
- reduce intent
- cap at P2 during the freeze window
- route to parent/integration decision authority when appropriate
## Business contraction
Signals such as major layoffs, closures, or sustained user decline may reduce commercial capacity.
Use as a negative modifier, not automatic disqualification.
## Founder/leadership transition
Can reduce buyer reachability and decision velocity.
Do not confuse this with product disqualification.
## Mature incumbent stack
If an enterprise-grade incumbent exists, investigate the gap.
Do not automatically suppress.
# 28. MULTIPLIERS / MODIFIERS
## India bridge
Use as a relationship/routing modifier only.
**Priority multiplier: ×1.25, rounded up**, if the defined India-bridge conditions are met.
Do not reinterpret this as buying intent.
## VAMP quantified-pain token
**Not scored.**
Use:
`monthly visits × 0.5%`
as a quantified fallback context where appropriate.
It supports personalization; it does not prove buying intent.
## Decision-maker depth bonus
If multiple relevant decision makers are identified with strong evidence, this can improve routing confidence.
It is a **reachability/routing modifier**, not intent.
# 29. SIGNAL / SCORE SAFETY RULES
The system must never:
- give high intent because the company simply looks like it needs security
- treat funding as proof of buying
- treat generic technology presence as intent
- treat evergreen regulation as a fresh trigger without an active event
- treat India affiliation as intrinsic intent
- present guessed problems as discovered incidents
- let one weak third-party signal force P1
- count duplicate copies of the same event as independent signals
- hide the evidence behind a score
# 30. PERSONALIZATION HIERARCHY
Choose the strongest **supported** reason for contacting the account.
1. Explicit company-specific security/fraud incident
2. Active security/compliance project
3. First-party product behavior
4. Security/fraud hiring
5. Relevant executive change
6. Architecture/replatforming
7. Expansion/product launch
8. Funding
9. Seasonal exposure
10. Quantified risk/context
11. Generic product value
Personalization must remain factual. Never convert hypothesis into fact.
# 31. MONITORING / RESEARCH CADENCE
<table header-row="true">
<tr>
<td>Signal source</td>
<td>Default cadence</td>
</tr>
<tr>
<td>First-party behavior</td>
<td>real-time / near-real-time</td>
</tr>
<tr>
<td>Explicit incidents</td>
<td>rapid/event-driven</td>
</tr>
<tr>
<td>LinkedIn / Indeed security & fraud hiring</td>
<td>weekly</td>
</tr>
<tr>
<td>Funding / executive news</td>
<td>weekly</td>
</tr>
<tr>
<td>Reddit / community discussions</td>
<td>weekly</td>
</tr>
<tr>
<td>G2 / review signals</td>
<td>weekly</td>
</tr>
<tr>
<td>BuiltWith / Wappalyzer changes</td>
<td>monthly</td>
</tr>
<tr>
<td>DNS / CNAME / well-known infrastructure</td>
<td>per domain or meaningful change</td>
</tr>
<tr>
<td>General business context</td>
<td>quarterly</td>
</tr>
</table>
Cadence should follow signal decay: the shorter the half-life, the more frequently the source should be refreshed.
# 32. ROUTING ORDER
Run these steps deterministically:
1. Compute ICP Fit.
2. Collect and date intent signals.
3. Score intent using weighted decay.
4. Apply negative/fractional suppression policies.
5. Check first-party behavior/PQL/PQA.
6. Apply relationship/routing modifiers.
7. Route to P1–P4.
8. Choose the strongest personalization hook.
9. Set next review date.
# 33. ROUTING MATRIX
```plain text
                         INTENT
                  LOW              HIGH
              ┌────────────────┬────────────────┐
HIGH FIT      │ P2             │ P1             │
              │ Trigger-watch  │ Act now        │
              ├────────────────┼────────────────┤
LOW/MED FIT   │ P4             │ P3             │
              │ Suppress       │ Opportunistic  │
              └────────────────┴────────────────┘
```
### P1 — Immediate
High fit + strong recent intent, or strong first-party buying behavior.
**Action:** personalized outreach rapidly.
### P2 — Trigger-watch
High fit + weak/stale intent.
**Action:** monitor for a new trigger; do not consume disproportionate manual outreach capacity.
### P3 — Opportunistic
Moderate fit with useful intent, or high intent with insufficient commercial/reachability fit.
**Action:** low-cost or templated outreach.
### P4 — Suppress
Weak fit + weak intent, or severe negatives.
**Action:** archive/suppress until the situation changes.
# 34. DECAY-AWARE REVIEW
Every scored lead should have:
`last_signal_date | strongest_signal | intent_score | next_review_date`
Review dates should follow the strongest active signal's half-life.
# 35. RESEARCH STOP CONDITIONS
Stop deep intent research when:
- evidence is already sufficient to determine P1/P2/P3/P4
- additional searches are returning duplicate or lower-quality evidence
- the account fails ICP hard gates
- a severe negative routing condition has been established
Do not search indefinitely for a stronger trigger that may not exist.
# 36. DATA MODEL
```plain text
domain
fit_score
commercial_fit
reachability_score
intent_score
priority

signal_types[]
signal_dates[]
signal_sources[]
signal_weights[]
signal_freshness[]
signal_confidence[]

A1_pain
A2_technology
A3_security_compliance_hiring
A4_competitor
A5_india
A6_business_change

negative_flags[]
behavior_signals[]
behavior_dates[]

pql_state
pqa_state

intent_primary_reason
intent_secondary_reason
personalization_angle
next_review_date
enrichment_next
```
# 37. A1–A6 OUTPUT CONTRACT
Required fields:
```plain text
buying_intent_A1_pain
buying_intent_A2_technology
buying_intent_A3_security_compliance_hiring
buying_intent_A4_competitor
buying_intent_A5_india
buying_intent_A6_business_change
```
Each field should retain, where applicable:
- finding
- source
- date
- relevance
- confidence
- whether it contributes to intent or is context only
# 38. CAMPAIGN ARCHITECTURE
> **Campaign universe = 1,200 Shopify leads.**
>
> **Current mid-market cohort = 485 leads with 50–500 employees.**
>
> The buying-intent framework applies to the full 1,200-lead campaign. The 485 cohort is the current mid-market self-serve focus; the remaining leads are not automatically discarded and should be classified using the ICP rather than the employee filter alone.
```plain text
1,200 Shopify leads
        ↓
ICP classification
        ↓
Decision-maker route
        ↓
A1–A6 + master intent signals
        ↓
Intent decay + negatives + behavior
        ↓
P1 / P2 / P3 / P4
        ↓
Personalization
        ↓
Outreach
```
# 39. WORKED EXAMPLE — STRONG ICP, LOW INTENT
```plain text
Company:
300 employees
1.8M visits
customer accounts
subscription model

FIT:
High

INTENT:
Low

Evidence:
No current incident
No security hiring
No relevant executive change
No active evaluation
No architecture migration

ROUTE:
P2

Reason:
Excellent ICP; insufficient current reason to buy now.
```
# 40. WORKED EXAMPLE — HIGH FIT, ACTIVE INTENT
```plain text
Company:
IoT device company
150 employees
250K active users

Recent signals:
- security engineer hired 10 days ago
- new authenticated device platform launched 18 days ago
- company-specific account-security discussion 7 days ago

FIT:
Very high
INTENT:
High
NEGATIVES:
None

ROUTE:
P1

BUYER ROUTE:
Security + CTO + Product
```
# 41. WORKED EXAMPLE — HIGH INTENT, LOW FIT
```plain text
Company:
35 employees
15K monthly users
company-specific compromise reported this week

INTENT:
High
FIT:
Low

ROUTE:
P3 or suppress depending on commercial capacity.

Reason:
The problem is real, but the current commercial ICP may not fit.
```
# 42. WORKED EXAMPLE — CORPORATE ROUTE
```plain text
Company:
Strong session consequence
Recent security incident

Intent:
High

Ownership:
Parent company controls security procurement

Local route:
P3 maximum under local-brand motion

Next:
Research parent security/technology/procurement owner.
```
# 43. PQL / PQA EXAMPLES
### PQL
```plain text
CTO visits docs twice
→ strong first-party signal
→ P1 candidate
```
### PQA
```plain text
CTO + Product leader + Security lead
all engage with docs/pricing
and account begins firing /evaluate
→ account-level evaluation
→ strongest routing class
```
# 44. QUALITY CONTROL CHECKLIST
Before a P1/P2 decision:
- [ ] ICP fit is separately established
- [ ] every material intent signal has a date
- [ ] source/evidence is retained
- [ ] stale signals have decayed
- [ ] duplicate signals are deduplicated
- [ ] solved/outdated incidents are downgraded
- [ ] A1–A6 are documented
- [ ] compliance is distinguished from active compliance intent
- [ ] India is not treated as intrinsic intent
- [ ] VAMP is not scored as buying intent
- [ ] negative routing caps are applied
- [ ] first-party behavior is checked
- [ ] score components are auditable
- [ ] personalization uses only supported facts
# 45. THREE-DOCUMENT ARCHITECTURE
**ICP** → Should Sentinel Layer care about this company?
**Decision Makers** → Who can move the purchase forward?
**Buying Intent** → Why should we act now?
Final system:
> **ICP Fit → Buyer Route → Intent → Priority → Personalization → Outreach**
The account can be an excellent ICP without being a good prospect today.
The Buying Intent system exists to capture that difference without allowing weak signals, stale events, or unsupported assumptions to manufacture urgency.
# 46. PERSONALIZATION AS A FORMAL SYSTEM LAYER
Personalization is not part of ICP qualification and does not replace Buying Intent.
The canonical chain is:
**ICP Fit → Buyer Route → Intent → Negatives → Behavior → Priority → Personalization → Outreach**
Definitions:
- **ICP Fit** = should SentinelLayer care?
- **Buyer Route** = who owns the relevant problem, capability, budget, or consequence?
- **Buying Intent** = why act now?
- **Personalization** = what verified evidence should shape what we say?
A personalization hook can exist without high buying intent. A high-intent account should still use the strongest verified personalization evidence available.
# 47. PERSONALIZATION EVIDENCE TAXONOMY
### P1 — Company-specific security or fraud pain
Examples:
- account takeover report
- unauthorized account access
- suspicious login
- unauthorized purchase after account compromise
- payout/account manipulation
- company-specific security failure affecting authenticated accounts
### P2 — Repeated customer security complaints
Multiple independent recent complaints describing materially similar account/security problems.
### P3 — Vendor / competitor dissatisfaction
Examples:
- named vendor coverage gap
- false positives
- pricing/contract dissatisfaction
- missing capability
- support/reactivity complaints
- explicit alternative/evaluation language
### P4 — Relevant community / dark-funnel evidence
Reddit, forums, developer/security communities, social discussions, and public customer complaints.
### P5 — First-party product behavior
Pricing, docs, trial, SDK/evaluation activity, multiple stakeholders, positive reply, or explicit information request.
### P6 — Organizational / technical triggers
Security/fraud hiring, executive change, replatforming, authenticated product launch, new market, funding, expansion.
### P7 — Contextual / quantified evidence
VAMP math, traffic, seasonality, business model, scale, and similar context.
# 48. SECURITY / NEGATIVE-REVIEW POLICY
A negative review is relevant only when it is:
- company-specific
- security/fraud/account related
- materially relevant to authenticated-session risk
- current enough to matter
- attributable to an actual observed experience
Do not treat the following as security evidence:
- generic bad-company sentiment
- shipping complaints
- generic customer-service complaints
- vague claims that security is terrible
- unrelated payment UX problems
- speculation
- complaints about another company
- duplicates of the same original complaint
## Review interpretation
If a customer says:
> “My account was hacked.”
The correct internal evidence is:
> Customer publicly reported unauthorized account access.
Not:
> Company experienced an account takeover.
The second claim requires independent corroboration.
# 49. PAIN EVIDENCE ≠ BUYING INTENT
A complaint demonstrates observed pain; it does not by itself prove that the company is actively evaluating security tooling.
### Example
One old security complaint:
- pain evidence: yes
- personalization: yes
- current intent: unknown
Three recent independent security complaints + security hiring + replatform:
- pain evidence: strong
- personalization: strong
- intent: materially stronger because independent categories corroborate
Maintain this distinction throughout scoring and routing.
# 50. REVIEW EVIDENCE STRENGTH
### Strong
Specific, recent, company-specific report involving authenticated-session security and a concrete consequence.
### Moderate
Several recent independent complaints describing similar account/security problems.
### Weak
Generic security dissatisfaction with no concrete event.
### Irrelevant
Negative sentiment unrelated to post-login security.
Additional corroboration can increase confidence but cannot justify unsupported claims.
# 51. PERSONALIZATION SOURCE HIERARCHY
Prefer:
1. direct company-specific evidence
2. repeated company-specific customer complaints
3. named vendor dissatisfaction / evaluation
4. relevant community discussion
5. category-level discussion
6. generic context
Provider count is not evidence count. Duplicate copies of one source do not create independent corroboration.
# 52. PERSONALIZATION TOKEN HIERARCHY
Use the strongest supported reason available:
1. explicit company-specific security/fraud pain
2. repeated company-specific security complaints
3. active security/compliance project
4. vendor/competitor dissatisfaction or evaluation
5. first-party product behavior
6. security/fraud hiring
7. relevant executive change
8. architecture/replatforming
9. authenticated product launch / expansion
10. funding
11. seasonal exposure
12. quantified risk/context
13. generic product value
Do not default to generic product value when stronger evidence exists.
# 53. CLAIM TYPES / CONFIDENCE
Every personalization result should distinguish:
- **OBSERVED** — directly supported by a source
- **CORROBORATED** — supported by multiple independent sources
- **INFERRED** — reasonable synthesis that must not be stated as fact
- **CONTEXT** — background information, not pain evidence
Outbound copy should use OBSERVED and CORROBORATED claims as facts. INFERRED material must be clearly qualified or omitted.
# 54. PERSONALIZATION DATA CONTRACT
Recommended fields:
personalization_angle
personalization_source
personalization_source_url
personalization_date
personalization_evidence
personalization_evidence_type
personalization_confidence
personalization_buyer_angle
personalization_claim_type
personalization_limitations
# 55. VAMP POSITIONING
VAMP remains a quantified-context token, not intent.
Use VAMP when stronger evidence is unavailable. Do not let it outrank:
- actual security pain
- repeated security complaints
- vendor dissatisfaction
- first-party evaluation
- explicit company-specific incidents
# 56. PERSONALIZATION QA
Before outreach:
- [ ] source resolves
- [ ] source supports the exact claim
- [ ] date retained
- [ ] stale evidence considered
- [ ] duplicates deduplicated
- [ ] customer complaint not upgraded into a confirmed incident
- [ ] pain evidence not mislabeled as buying intent
- [ ] buyer angle matches the buyer's ownership
- [ ] inference separated from observation
- [ ] generic complaint not presented as company-specific
- [ ] message does not imply unearned familiarity
The complete operational policy is maintained in <mention-page url="https://app.notion.com/p/3ddb4f1d1069819bbb2ddb8fdef2426d"/>.