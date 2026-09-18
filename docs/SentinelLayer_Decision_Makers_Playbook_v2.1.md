<callout icon="👥" color="blue_bg">
	**Homepage placement:** Canonical decision-maker selection and routing playbook.
</callout>
# Status
Canonical operating playbook for identifying, prioritizing, validating, routing, and researching the people who can buy, approve, champion, block, or materially influence Sentinel Layer.
**Parent:** ICP v2.1  
**Companion:** Buying Intent Classification & Routing v3.2
# 1. PURPOSE
The ICP answers:
> **Which companies should Sentinel Layer care about?**
This document answers:
> **Who inside those companies should we contact, in what order, why do they care, and what evidence supports that conclusion?**
Buying Intent separately answers:
> **Why now?**
# 2. CORE PRINCIPLE
Do not choose decision makers primarily by title.
Choose them by **ownership of the problem created by the company's authenticated sessions**.
The correct question is not:
> "Who is the CTO?"
It is:
> "Who owns the risk, capability, budget, implementation, or consequence associated with what can happen inside this company's authenticated sessions?"
# 3. BUYING COMMITTEE MODEL
A typical opportunity contains five functional roles:
### 1. Problem Owner
Feels or owns the consequence of session compromise.
Examples:
- Security
- Fraud/Risk
- Finance
- Operations
- Legal/Privacy
- Customer Support
### 2. Technical Approver
Must approve or implement the integration.
Usually:
- CTO
- VP Engineering
- Head of Engineering
- Security Engineering
### 3. Economic Buyer
Can approve the spend or materially control the budget.
Usually:
- Founder/CEO
- COO
- CFO/CFOO
- business-unit leader
### 4. Product Owner
Controls the user/session experience and determines where instrumentation can be deployed.
Usually:
- Head of Product
- CPO
- Head of Digital/E-commerce
- IoT/Product leader
### 5. Champion / Influencer
Experiences the pain or can create internal momentum but may not own budget.
Examples:
- Fraud/Risk
- Support/CX
- Staff Engineer
- Head of E-commerce
- Trust & Safety
Not every company has all five.
The enrichment system should identify the smallest viable buying committee rather than mechanically finding every executive.
# 4. FIRST PRINCIPLE: MAP THE BUYER TO THE SESSION CONSEQUENCE
Decision-maker selection starts with the highest-consequence capability identified in the ICP.
<table header-row="true">
<tr>
<td>Session consequence</td>
<td>Primary buyer</td>
<td>Technical approver</td>
<td>Economic buyer</td>
<td>Secondary thread</td>
</tr>
<tr>
<td>Physical-device control</td>
<td>Security / CTO</td>
<td>CTO / Engineering</td>
<td>CEO / COO</td>
<td>Product / IoT</td>
</tr>
<tr>
<td>Money movement / payout</td>
<td>Finance / Risk</td>
<td>CTO / Engineering</td>
<td>CFO / COO / CEO</td>
<td>Security</td>
</tr>
<tr>
<td>Health data</td>
<td>Security / Privacy</td>
<td>CTO / Engineering</td>
<td>CEO / COO</td>
<td>Legal / Product</td>
</tr>
<tr>
<td>Children's data</td>
<td>Security / Privacy</td>
<td>CTO / Engineering</td>
<td>CEO / COO</td>
<td>Legal</td>
</tr>
<tr>
<td>Privileged SaaS/admin access</td>
<td>Security</td>
<td>CTO / Engineering</td>
<td>CEO / COO</td>
<td>Product / Risk</td>
</tr>
<tr>
<td>Bulk export / sensitive data</td>
<td>Security / Risk</td>
<td>CTO / Engineering</td>
<td>CEO / COO</td>
<td>Legal / Product</td>
</tr>
<tr>
<td>Subscription/payment state</td>
<td>Finance / Risk</td>
<td>CTO / Engineering</td>
<td>CFO / COO / CEO</td>
<td>E-commerce</td>
</tr>
<tr>
<td>High-ticket purchase</td>
<td>Fraud/Risk / Finance</td>
<td>CTO / Engineering</td>
<td>CFO / COO</td>
<td>E-commerce</td>
</tr>
<tr>
<td>Drop/community abuse</td>
<td>E-commerce / Trust & Safety</td>
<td>CTO / Engineering</td>
<td>CEO / COO</td>
<td>CX</td>
</tr>
<tr>
<td>General account protection</td>
<td>CTO / Security</td>
<td>CTO / Engineering</td>
<td>Founder / COO</td>
<td>E-commerce</td>
</tr>
</table>
This table is more important than a static executive hierarchy.
# 5. ROUTING CLASSES
## P0 — Must find
A person whose involvement is required to understand or advance the opportunity.
Normally:
- CISO / Head of Security
- CTO / VP Engineering
- Founder/CEO in small companies
- Head of Fraud/Risk where the function exists
## P1 — Second thread
Important buyer, economic stakeholder, or cross-functional approver.
Examples:
- COO/CFOO
- CFO/Finance
- Head of Product
- General Counsel / Privacy
- Head of Payments
- Head of E-commerce
## P2 — Champion / influencer
Can create urgency or provide internal access but generally does not control the purchase.
Examples:
- Head of Support
- Trust & Safety
- Staff Engineer
- E-commerce Director
- Fraud Operations
## P3 — Do not prioritize
Relevant to the company but not the purchase.
Examples:
- CMO
- Brand Director
- Creative Director
- Logistics
- Supply Chain
Do not spend enrichment budget hunting P3 roles unless evidence indicates unusual ownership.
# 6. PRIMARY BUYER — CISO / SECURITY
## Titles
Search for:
- CISO
- Chief Information Security Officer
- Head of Security
- VP Security
- Director of Security
- Information Security Director
- Information Security Manager
- Security Lead
- Security Architect
- Security Engineer
- Cloud Security
- Application Security
- Product Security
- Trust & Safety
- Risk & Security
## Why they care
Potential ownership includes:
- session security
- account takeover
- anomaly detection
- incident response
- access control
- security monitoring
- SOC 2
- ISO 27001
- privacy/security obligations
- security architecture
## When they become #1
Promote Security to the top of the research queue when any of these are present:
- physical-device control
- health data
- children's data
- financial access
- privileged enterprise data
- substantial compliance exposure
- existing security organization
- explicit fraud/risk/security hiring
- existing fraud/security tools
## When not to over-search
At 50–500 employees, a dedicated CISO may not exist.
Do not spend excessive enrichment time trying to invent one.
If no security leader exists:
> **CTO/Engineering becomes the primary technical security buyer.**
# 7. PRIMARY BUYER — CTO / VP ENGINEERING
## Titles
- CTO
- Chief Technology Officer
- VP Engineering
- Head of Engineering
- Director of Engineering
- Head of Technology
- VP Technology
- Engineering Manager
- Technical Director
## Why they care
Sentinel Layer touches:
- authentication/session infrastructure
- backend routing
- application instrumentation
- risk-event generation
- application response logic
They must determine whether the integration is safe, practical, and maintainable.
The implementation is intentionally lightweight:
- SDK
- one backend proxy
- existing authentication remains in place
- server-side key
- risk response returned to the application
## When CTO is #1
Make CTO the first technical target when:
- no CISO exists
- no security leader exists
- company is roughly 50–250 employees
- product is technically complex
- application/session security is engineering-owned
# 8. PRIMARY ECONOMIC BUYER — FOUNDER / CEO
## Titles
- Founder
- Co-founder
- CEO
- Owner
- President
## Why they care
At smaller companies the founder frequently owns:
- P&L
- risk tolerance
- security priorities
- vendor approvals
- major operational decisions
## When Founder becomes #1
Prioritize when:
- \<150 employees
- founder remains operationally active
- no obvious security/technology leader
- self-serve purchase is plausible
- company is founder-led/independent
- clear business consequence exists
## When Founder should not be the only target
At larger organizations, use:
> **Technical buyer + economic/operational buyer**
rather than assuming CEO is the best route.
# 9. COO / CFOO / OPERATIONS / FINANCE
## Titles
- COO
- Chief Operating Officer
- CFOO
- Chief Financial and Operating Officer
- Head of Operations
- VP Operations
- CFO
- VP Finance
- Head of Finance
- Controller
## Why they care
They may own:
- dispute cost
- payment operations
- operational losses
- support burden
- chargeback exposure
- margin
- financial risk
## When to prioritize
Strong candidate when:
- 150–500 employees
- subscription revenue
- high-ticket products
- significant payment volume
- payout/account-change exposure
- finance leader owns operational risk
Usually use this as a co-thread with CTO rather than replacing technical ownership.
# 10. FRAUD / RISK / TRUST & SAFETY
## Titles
- Head of Fraud
- Fraud Director
- Fraud Manager
- Risk Director
- Head of Risk
- Risk Operations
- Fraud Operations
- Trust & Safety
- Trust & Safety Lead
- Abuse Prevention
## Importance
Promote this role whenever it exists.
They may already have an explicitly recognized problem:
> suspicious behavior, fraud, abuse, account compromise, or risk.
That can make them one of the strongest champions.
## Critical distinction
They may be:
- excellent problem owner
- excellent champion
- poor technical approver
Therefore:
> **Fraud/Risk + CTO**
is often stronger than Fraud/Risk alone.
# 11. HEAD OF PRODUCT / CPO
## Titles
- CPO
- Head of Product
- VP Product
- Director of Product
- Product Lead
- Head of IoT
- Head of Hardware
## Why they care
They control:
- user journey
- account flows
- sensitive actions
- instrumentation points
- step-up authentication UX
- product-level tradeoffs
## Promote to P1 when
- IoT
- device control
- health products
- quiz/personalization systems
- account-heavy consumer applications
- authentication is deeply tied to product UX
# 12. HEAD OF E-COMMERCE / DIGITAL
## Titles
- Head of E-commerce
- VP E-commerce
- E-commerce Director
- Head of Digital
- Director of Digital
- Head of DTC
- Digital Commerce Director
## Why they matter
They often understand:
- customer accounts
- checkout
- subscriptions
- payments
- customer complaints
- account abuse
- Shopify operations
They can become strong internal champions.
## Limitation
They are generally **not the default technical buyer**.
Best route:
> E-commerce champion → CTO/security introduction.
# 13. HEAD OF PAYMENTS / FINANCE
## Titles
- Head of Payments
- Payments Director
- VP Payments
- Head of Finance
- Controller
- Treasurer
- Payments Operations
- Revenue Operations
## Promote when
- payout modification exists
- recurring billing
- high-ticket financing
- significant payment exposure
- dispute/chargeback signals
- processor-risk concerns
# 14. GENERAL COUNSEL / PRIVACY / LEGAL
## Titles
- General Counsel
- Chief Legal Officer
- Head of Legal
- Privacy Counsel
- Data Protection Officer
- Chief Privacy Officer
- Associate General Counsel
## Promote when
- children's data
- health data
- significant privacy exposure
- age-gated products
- breach exposure
- major regulatory requirements
- enterprise procurement/security review
## Limitation
Legal is usually a risk stakeholder rather than the technical buyer.
Normal route:
> **Security/CTO + Legal/Privacy**
# 15. CUSTOMER SUPPORT / CX
Usually:
**Champion / pain witness**
They hear:
> "Someone accessed my account."
They may experience:
- account takeover tickets
- address changes
- unauthorized subscriptions
- compromised accounts
- fraud complaints
They rarely own the security budget.
Use them to establish pain and create an internal introduction.
# 16. STAFF / PRINCIPAL ENGINEER
Potential bottom-up implementation champion.
Relevant when:
- technical organization exists
- no CTO response
- integration simplicity is a major concern
- security engineering is decentralized
They can establish whether:
- SDK can be deployed
- proxy route is acceptable
- authentication flow is compatible
- instrumentation is feasible
They usually do not control final purchasing.
# 17. PE OPERATING PARTNER / PARENT SECURITY LEAD
Corporate ownership changes the buying map.
If a brand is owned by PE, a strategic corporation, holding company, or large public parent, determine whether security/vendor decisions are centralized.
### If local authority exists
Target:
- local CTO
- local E-commerce
- local operations
- local security
### If decisions are centralized
Search:
- parent CISO
- parent security leader
- parent digital/technology leader
- parent procurement
- operating partner
- portfolio operations
Do not pretend a local Shopify executive can approve a parent-controlled vendor.
# 18. COMPANY-SIZE DECISION TREE
## 50–149 employees
Default sequence:
1. Security, if present
2. CTO/Engineering
3. Founder/CEO
4. Product or Finance depending on consequence
Founder remains highly relevant because the organization is usually less functionally segmented.
## 150–500 employees
Default sequence:
1. Security, if present
2. CTO/VP Engineering
3. COO/CFOO/Finance
4. Product/E-commerce
5. Founder/CEO as economic sponsor when appropriate
Do not automatically put Founder first.
## Corporate / PE owned
Default sequence:
1. Determine decision authority
2. If centralized → parent owner
3. If local → local CTO/security + operational buyer
4. Use operating partner when portfolio-wide security opportunity exists
# 19. BUYER SELECTION BY SESSION ARCHETYPE
## Physical device
1. Security
2. CTO/Engineering
3. Product/IoT
4. CEO/COO
## Financial / payout
1. Risk/Fraud
2. Finance/Payments
3. CTO
4. Security
5. COO/CEO
## Health data
1. Security
2. CTO
3. Legal/Privacy
4. Product
5. CEO/COO
## Children's data
1. Security
2. Legal/Privacy
3. CTO
4. Product
5. CEO/COO
## Privileged SaaS/business data
1. Security
2. CTO
3. Product
4. Risk
5. CEO/COO
## Subscription/high-ticket commerce
1. CTO
2. Finance/Payments
3. E-commerce
4. Security
5. COO/CEO
## General customer-account protection
1. CTO
2. Founder/CEO or COO
3. Security if present
4. E-commerce/Product
# 20. MINIMUM BUYING COMMITTEE
For the current self-serve motion, the default is:
> **Technical buyer + economic/problem buyer**
Typical pairs:
- CTO + Founder
- CTO + COO
- CTO + CFO
- CISO + CTO
- Security + COO
- Fraud/Risk + CTO
Add a third stakeholder only when:
- session consequence is unusually high
- procurement is complex
- regulatory/legal exposure exists
- product integration requires a distinct owner
- parent approval is likely
# 21. MAXIMUM RESEARCH DEPTH
Decision-maker enrichment should be proportional to account value.
<table header-row="true">
<tr>
<td>Lead quality</td>
<td>Research depth</td>
</tr>
<tr>
<td>Non-ICP</td>
<td>Stop</td>
</tr>
<tr>
<td>Conditional ICP</td>
<td>1–2 people</td>
</tr>
<tr>
<td>Strong ICP</td>
<td>2–3 people</td>
</tr>
<tr>
<td>Exceptional / P1 candidate</td>
<td>3–5 people</td>
</tr>
<tr>
<td>Strategic / parent-owned</td>
<td>Establish decision authority first</td>
</tr>
</table>
The objective is:
> **maximum decision coverage per unit of research effort**
not maximum names.
# 22. SEARCH ORDER
1. Official leadership/team page
2. Official company/executive page
3. LinkedIn/company people pages
4. Reliable executive databases
5. Press releases, filings, interviews, conference bios
6. Search-engine discovery
Role-specific searches identify candidates; final records require actual supporting evidence.
# 23. SEARCH QUERY PATTERNS
### Security
`site:linkedin.com/in "[company]" ("CISO" OR "Head of Security" OR "VP Security")`
### Engineering
`site:linkedin.com/in "[company]" ("CTO" OR "VP Engineering" OR "Head of Engineering")`
### Founder
`site:linkedin.com/in "[company]" ("Founder" OR "CEO" OR "Co-founder")`
### Finance
`site:linkedin.com/in "[company]" ("CFO" OR "CFOO" OR "VP Finance" OR "Head of Finance")`
### Product
`site:linkedin.com/in "[company]" ("CPO" OR "Head of Product" OR "VP Product")`
### Legal
`site:linkedin.com/in "[company]" ("General Counsel" OR "Privacy Counsel" OR "DPO")`
### Fraud/Risk
`site:linkedin.com/in "[company]" ("Fraud" OR "Risk" OR "Trust & Safety")`
### E-commerce
`site:linkedin.com/in "[company]" ("Head of E-commerce" OR "Director of E-commerce" OR "Head of Digital")`
These are discovery queries, not evidence by themselves.
# 24. EVIDENCE-ONLY CONTRACT
## Rule 1 — Never fabricate a person
If evidence does not establish the individual:
> `NO_DM_FOUND — reason: no reliable source surfaced after defined searches`
is correct.
## Rule 2 — Never fabricate a source
Every URL recorded must be a URL actually found/fetched during the enrichment session.
## Rule 3 — Never self-assign validator labels
Do not write:
- VERIFIED
- INFERRED
- NOT_FOUND
inside output fields. The validator owns those classifications.
## Rule 4 — Separate person evidence from email inference
A person can be supported by a source while their email remains only a pattern guess.
## Rule 5 — Generic email is separate
`support@domain` does not become `decision_maker_email`.
## Rule 6 — NO_DM_FOUND is valid
An honest empty result is preferable to fabricated data.
## Rule 7 — Every URL must be session-supported
An uncited plausible URL is still unsupported.
# 25. EMAIL DECISION-MAKER FIELD
The field may contain a pattern guess when the person's identity is supported.
The output should be the address only.
Do not append verification claims unless independently evidenced in the proper evidence field.
# 26. EMAIL PATTERN RESEARCH
Preferred evidence hierarchy:
1. actual published company/person email
2. company email format observed elsewhere
3. repeated sibling-address pattern
4. standard pattern inference
Email-pattern likelihood is **not identity evidence**.
# 27. COMPANY EMAIL
The company generic field remains available even when no personal decision-maker is found.
Examples:
- support@
- hello@
- partnerships@
- press@
- info@
Generic company contacts and personal decision-maker addresses are separate fields.
# 28. ANTI-PERSONAS
Do not prioritize:
- CMO
- Marketing Director
- Brand Director
- Creative Director
- Social Media Director
- Logistics
- Supply Chain
- Warehouse Operations
- Merchandising
unless evidence shows explicit ownership of:
- account security
- fraud
- payments
- customer identity
- trust & safety
# 29. SPECIAL CASE — NO CISO
Do not interpret:
> no CISO
as:
> no security buyer.
Security may be distributed among:
- CTO
- VP Engineering
- Head of Infrastructure
- Engineering Manager
- Security Engineer
- IT/Security leader
Absence of a CISO changes the route; it does not invalidate ICP.
# 30. SPECIAL CASE — NO CTO
Search for:
- VP Engineering
- Head of Engineering
- Director Engineering
- Head of Technology
- Technical Founder
- Lead Engineer
- CIO
For smaller companies:
> **Founder + senior engineer**
may be the practical buying pair.
# 31. SPECIAL CASE — PARENT-OWNED COMPANY
First establish:
> **Who can actually approve a \$99–\$499/month security vendor?**
Possible answers:
- local e-commerce leader
- local CTO
- local COO
- parent security
- parent technology
- parent procurement
- PE operating partner
The answer determines outreach routing.
# 32. SPECIAL CASE — HIGH-CONSEQUENCE ICP
For:
- IoT
- financial access
- health
- children's data
- privileged SaaS
research depth should increase.
Recommended:
**3–4 stakeholders minimum** where they can be reliably found.
# 33. SPECIAL CASE — LOW-CONSEQUENCE ICP
For generic low-risk DTC:
1. CTO/Engineering
2. Founder/COO/E-commerce
Stop unless evidence suggests a stronger session consequence.
# 34. PERSONALIZATION OWNERSHIP
The person contacted determines the opening argument.
### Security
Lead with:
- session anomaly detection
- behavioral baseline
- account takeover
- monitoring
- security controls
- architecture
### CTO
Lead with:
- implementation burden
- SDK size
- proxy architecture
- no auth migration
- server-side key
### Founder/CEO
Lead with:
- financial exposure
- customer harm
- business risk
- concrete consequence
- low-cost self-serve adoption
### CFO/COO
Lead with:
- operational loss
- dispute cost
- fraud cost
- processor exposure
- financial consequences
### Product
Lead with:
- account experience
- selective step-up
- preserving conversion
- instrumentation placement
### Legal/Privacy
Lead with:
- exposure
- incident consequences
- security controls
- regulatory obligations
### Fraud/Risk
Lead with:
- account takeover
- suspicious session behavior
- post-login anomalies
- reduced investigation burden
# 35. CONTACT STRATEGY
Use **multi-threading**, not executive spraying.
### Thread 1
Technical buyer.
### Thread 2
Economic/problem owner.
### Thread 3 only when justified
Product, Legal, Payments, or parent security.
The goal is independent paths to the same buying decision.
# 36. RESEARCH STOP CONDITIONS
Stop when:
- a strong technical buyer is found
- a strong economic/problem buyer is found
- identities and supporting sources are adequately documented
- further searches produce weaker candidates
Do not spend another ten minutes finding the sixth executive when the buying committee is already adequately covered.
# 37. OUTPUT SCHEMA
Recommended representation:
```plain text
domain
decision_makers
decision_maker_roles
decision_maker_priority
decision_maker_rationale
linkedin
decision_maker_email
company_email
ownership_route
technical_buyer
economic_buyer
problem_owner
champion
session_archetype
buyer_hook
evidence_urls
enrichment_confidence
enrichment_next
```
For compatibility with the existing pipeline, retain:
```plain text
decision_makers
linkedin
decision_maker_email
company_email
```
# 38. CAMPAIGN SCOPE
> **Campaign universe = 1,200 Shopify leads.**
>
> **Current mid-market cohort = 485 leads with 50–500 employees.**
>
> Decision-maker methodology applies to **all 1,200 leads**. Research depth and routing are determined by ICP fit and session consequence; the 485 cohort receives the current mid-market self-serve focus.
# 39. QUALITY CONTROL
Before a lead becomes DM-ready:
### Identity
- decision-maker name supported
- title supported
- relevant role relationship supported
### Source integrity
- every URL actually retrieved
- no invented source attribution
- no unsupported names
### Email
- personal and company email separated
- guesses not represented as facts
### Coverage
- technical buyer identified
- economic/problem buyer identified where possible
- special-role buyer added for high-consequence sessions
### Routing
- session archetype identified
- buyer order applied
- ownership structure considered
### Hygiene
- no self-written validator labels
- no fabricated confidence
- NO_DM_FOUND acceptable when justified
# 40. FINAL RULE
**Decision relevance \> title prestige**
**Evidence \> completeness**
**Buying coverage \> number of names**
**Session consequence \> generic executive hierarchy**
**Research efficiency \> maximum enrichment**
# 41. THREE-DOCUMENT ARCHITECTURE
**ICP** → Which companies fit?
**Decision Makers** → Who inside can move the purchase forward?
**Buying Intent** → Why act now?
Final chain:
> **ICP Fit → Buyer Route → Intent → Priority → Personalization → Outreach**
# 42. SECURITY / CUSTOMER-COMPLAINT EVIDENCE ROUTING
Public complaints can reveal the **problem owner**, but the complaint source is not automatically the buyer.
### Account takeover / unauthorized access
Primary:
- Security / Risk
- CTO / VP Engineering
Secondary:
- Product
- Founder / COO
### Unauthorized transaction / payout manipulation
Primary:
- Fraud / Risk
- Finance / Payments
Secondary:
- CTO / Engineering
### Account lockout / suspicious-login friction
Primary:
- Product
- CTO / Engineering
Secondary:
- Support / CX
- Security
The key question is:
> **Who owns the underlying problem described by the evidence?**
Support/CX may be an excellent evidence source or champion when customers repeatedly report the issue, but should not automatically be treated as the economic buyer.
# 43. BUYER-SPECIFIC PERSONALIZATION FROM PAIN EVIDENCE
The same evidence should be translated differently depending on the buyer.
<table header-row="true">
<tr>
<td>Evidence</td>
<td>Security / Risk</td>
<td>CTO / Engineering</td>
<td>Product</td>
<td>Finance / COO</td>
<td>Support / CX</td>
</tr>
<tr>
<td>Account takeover complaint</td>
<td>session anomaly / ATO detection</td>
<td>session instrumentation / integration</td>
<td>selective step-up</td>
<td>loss / operational exposure</td>
<td>repeat hacked-account workload</td>
</tr>
<tr>
<td>Unauthorized transaction</td>
<td>fraud/session abuse</td>
<td>request-level controls</td>
<td>safer account/checkout action</td>
<td>direct financial leakage</td>
<td>dispute/support volume</td>
</tr>
<tr>
<td>Account lockout</td>
<td>distinguish attack from user friction</td>
<td>auth/session telemetry</td>
<td>reduce unnecessary friction</td>
<td>support cost</td>
<td>ticket volume</td>
</tr>
<tr>
<td>Privacy complaint</td>
<td>sensitive-session protection</td>
<td>implementation/data path</td>
<td>trust and UX</td>
<td>exposure cost</td>
<td>customer trust</td>
</tr>
<tr>
<td>Vendor dissatisfaction</td>
<td>capability gap</td>
<td>replacement / augmentation</td>
<td>product impact</td>
<td>cost / ROI</td>
<td>operational coverage</td>
</tr>
</table>
# 44. EVIDENCE CONTRACT FOR CUSTOMER REVIEWS
Before using a customer review or public complaint in a message:
- source must actually exist and resolve
- source must support the stated claim
- company/product must be identifiable
- security relevance must be explicit enough to support the claim
- date should be retained
- duplicate copies of the same complaint are not independent evidence
- vague sentiment should not be upgraded into an incident
- historical/resolved issues should be treated as historical evidence
- uncertainty must remain visible
Never write:
> “Your customers are getting hacked.”
when the evidence is one review.
Prefer:
> “I noticed a customer report describing unauthorized account access…”
when that is exactly what was observed.
Personalization rules are maintained in the canonical <mention-page url="https://app.notion.com/p/3ddb4f1d1069819bbb2ddb8fdef2426d"/>.