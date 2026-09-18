<callout icon="🎯" color="blue_bg">
	**Homepage placement:** Canonical ICP reference for SentinelLayer GTM and lead qualification.
</callout>
# Status
Canonical source of truth for list building, qualification, enrichment, scoring, DM copy, segmentation, and GTM decisions.
# 1. EXECUTIVE DEFINITION
## The actual ICP
> **A company with externally accessible authenticated user sessions where a compromised session can perform a meaningful action, access sensitive information, move money, change account state, control a device, or create material business/reputational harm—and where the company is commercially capable of adopting a \$99–\$499/month self-serve security product.**
The primary current segment is:
> **US mid-market e-commerce/DTC companies with customer accounts and meaningful post-login value.**
The next expansion segment is:
> **B2B SaaS, fintech, HR/payroll, and other software businesses with externally accessible user sessions containing sensitive data or privileged capabilities.**
**Important:** Shopify is a prospecting source, not an ICP requirement. Sentinel Layer is stack-agnostic and protects authenticated sessions regardless of whether the application uses Shopify, WooCommerce, Rails, Django, Laravel, Next.js, or another stack.
# 2. PRODUCT–PROBLEM DEFINITION
Sentinel Layer protects the period **after authentication**.
Authentication answers:
> "Are these credentials valid?"
Sentinel Layer asks:
> "Does what is happening inside this authenticated session still look legitimate?"
It evaluates behavioral signals during a live session and returns a risk score from 0–100 plus a recommended action such as:
- ALLOW
- STEP_UP_AUTH
- BLOCK
The application ultimately decides what to do.
The integration is intentionally lightweight:
- \~5KB gzipped SDK
- zero dependencies
- client SDK + one backend proxy
- API key remains server-side
- fails open by design
- stack-agnostic
These implementation characteristics matter commercially, but **they are not ICP requirements**.
# 3. THE FUNDAMENTAL ICP MODEL
A company is attractive when four things overlap:
### A. Authenticated session exists
There is an external user/customer/account login.
### B. The session has meaningful privilege or value
The user can do something important after login.
### C. Compromise has meaningful consequences
An attacker controlling the session could create financial, operational, privacy, security, physical, or reputational damage.
### D. The company can realistically buy
There is sufficient organizational and commercial maturity to purchase and deploy the product through the current self-serve motion.
This produces the core model:
> **Session existence × Session privilege/value × Consequence severity × Commercial ability**
Traffic, employee count, revenue, funding, technology, and regulatory exposure are supporting commercial/context variables, not substitutes for the core product problem.
# 4. HARD ICP REQUIREMENTS
## 4.1 External authenticated session
The company must have a customer, user, member, administrator, practitioner, employee-facing external portal, or similar authenticated surface.
Examples:
- e-commerce customer account
- SaaS dashboard
- payroll account
- financial account
- practitioner portal
- subscription account
- IoT companion application
- marketplace seller account
- admin/customer portal
### Disqualifier
No meaningful external authentication surface.
Examples:
- pure catalog website
- marketing-only website
- wholesale-only site with no customer portal
- internal tool with no external users
## 4.2 Meaningful post-login capability
A login by itself is not sufficient.
The authenticated session must allow the user to perform or access something valuable.
### Very strong examples
- change payout/bank information
- change password/security settings
- modify account ownership information
- access health information
- access children's information
- initiate financial transactions
- access stored payment information
- export large datasets
- access business/customer records
- control physical devices
- access API keys or privileged controls
- modify subscriptions
- perform high-value purchases
- manage organizational resources
### Weak example
Login only exposes basic order history with no sensitive information, privileged capability, or important state change.
# 5. SESSION PRIVILEGE / CONSEQUENCE MODEL
This is a first-class ICP dimension.
## Critical
The session can control the physical world or move/control significant money.
Examples:
- smart locks
- cameras
- connected medical devices
- connected appliances
- payout accounts
- financial transfers
- privileged infrastructure
## High
The session exposes or modifies highly sensitive information or important account state.
Examples:
- health/wellness data
- children's data
- employee/payroll information
- customer PII
- sensitive financial information
- account-recovery/security settings
- bulk exports
- privileged SaaS operations
## Medium
The session controls recurring financial or commercial state.
Examples:
- subscription management
- payment methods
- financing
- high-value orders
- shipping/address changes
- marketplace seller operations
## Low
The session primarily exposes low-sensitivity information with limited ability to cause harm.
Examples:
- basic order history
- preference settings
### Rule
**Low session value should materially reduce ICP priority even when the company has large traffic or many employees.**
Traffic alone is not enough.
# 6. COMMERCIAL FIT
## Preferred company size
**50–500 employees**
Why:
- enough operational complexity to have meaningful security/risk exposure
- enough revenue to justify security tooling
- still compatible with the current self-serve price point
- generally less procurement friction than large enterprise accounts
### Exception rule
Employee count is **not an absolute product-fit requirement**.
A smaller company may still be highly attractive when session consequence is extremely high.
Examples:
- IoT physical-device control
- financial access
- high-value payouts
- sensitive health data
- critical B2B administrative controls
A 300-person company can be a weak ICP if its authenticated sessions have little value.
# 7. SESSION VOLUME / SCALE
## Preferred
**≥100K monthly authenticated sessions/users or a defensible proxy for session volume.**
For e-commerce, website traffic is an imperfect proxy because anonymous visits are not necessarily authenticated sessions.
For apps and SaaS, use:
- MAU
- authenticated users
- active accounts
- application sessions
- customer portal activity
where available.
## Exception
Below 100K may still qualify where:
- session privilege is critical/high
- individual compromise has high economic or safety consequences
- the account has strong regulatory/security sensitivity
## Upper bound
The original 100K–5M range is useful for the **current mid-market self-serve motion**, but \>5M should not automatically disqualify a company.
Instead:
> **\>5M = investigate enterprise security stack/procurement before investing heavy outbound effort.**
This is a commercial-motion issue, not proof that Sentinel Layer cannot solve the problem.
### Campaign scope
> **Campaign universe = 1,200 Shopify leads.**
>
> **Current mid-market cohort = 485 leads with 50–500 employees.**
>
> The 485 figure is a current sourcing cohort, not the definition of the entire Sentinel Layer ICP.
# 8. VERTICAL PRIORITY
## Priority 1 — E-commerce / DTC
**Current primary GTM segment.**
Reason:
- strongest available lead source
- shortest path to founder/COO/CTO
- straightforward deployment
- large prospect pool
- simple product explanation
- Shopify ecosystem provides useful prospecting data
### Tier A++ — exceptional session consequence
#### 1. IoT / app-connected devices
Examples:
- smart locks
- cameras
- pet devices
- purifiers
- sprinklers
- medical/wellness devices
- connected home equipment
Why: post-login compromise can affect the physical world.
#### 2. Kids / minors
Examples: products/services involving children's accounts or sensitive children's information.
Why: sensitive minor data increases consequence severity and regulatory exposure.
#### 3. Health / wellness data
Examples:
- cycle tracking
- fertility
- glucose
- medical/wellness records
- treatment-related information
- sensitive health profiles
Why: compromise can create privacy, safety, reputational, and regulatory consequences.
### Tier A — strong session value
#### Drop / limited-release brands
Signals:
- drops
- limited releases
- sell-outs
- scalping
- bot activity
- waitlists
#### Creator/community-led brands
Trust and community are part of the economic moat. Use primarily as a consequence/personalization amplifier, not as a standalone reason to qualify.
#### Age-gated commerce
Examples: alcohol, cannabis, other legally age-restricted commerce.
#### High-ticket commerce / financing
Examples: e-bikes, motorcycles, premium electronics, large appliances and other high-value purchases.
### Tier B
- subscription/recurring billing
- practitioner/professional portals
- franchise/multi-location
- marketplace/seller accounts
- other businesses where authenticated accounts materially affect revenue
These generally require stronger session-value evidence before being treated as top-tier.
## Priority 2 — B2B software
Next expansion after the e-commerce motion is validated.
### Highest-potential categories
- B2B SaaS with sensitive business data
- HRMS/payroll
- fintech/payments
- EdTech/student systems
- vertical SaaS/customer portals
## Priority 3 — Opportunistic
Do not proactively build large lists until the first two segments prove repeatable.
Examples:
- consumer fintech
- gaming
- marketplaces
- booking platforms
- other account-based consumer applications
# 9. TECHNOGRAPHICS
## Technology is NOT the ICP
Sentinel Layer is stack-agnostic.
Possible environments include:
- Shopify
- Shopify Plus
- WooCommerce
- custom applications
- Rails
- Django
- Laravel
- Next.js
- Node applications
- SaaS platforms
- IoT companion applications
- Auth0
- Okta
- Cognito
- Firebase
- Clerk
- Supabase
- custom authentication
The presence of Shopify is useful for prospecting and integration simplicity, not because Shopify itself creates product-market fit.
# 10. TECHNOGRAPHIC AMPLIFIERS
These increase attractiveness but do not define the ICP.
### Authentication infrastructure
Useful evidence:
- Auth0
- Okta
- Cognito
- Firebase
- Clerk
- Supabase
- custom authentication
### Recurring billing
Examples:
- Recharge
- Skio
- Bold
- native subscriptions
### Payment infrastructure
Examples:
- Stripe
- Shopify Payments
- Adyen
### App-connected hardware
Strongest technographic amplifier because the account can control the physical world.
# 11. DATA SENSITIVITY HIERARCHY
<table header-row="true">
<tr>
<td>Severity</td>
<td>Session value</td>
<td>ICP effect</td>
</tr>
<tr>
<td>Critical</td>
<td>Physical-device control / major financial control</td>
<td>Exceptional fit</td>
</tr>
<tr>
<td>High</td>
<td>Health data / children's data / privileged enterprise data</td>
<td>Very strong fit</td>
</tr>
<tr>
<td>High</td>
<td>Admin controls / bulk exports / account-security controls</td>
<td>Very strong fit</td>
</tr>
<tr>
<td>Medium</td>
<td>Stored payment methods / subscription / financing</td>
<td>Strong fit</td>
</tr>
<tr>
<td>Medium</td>
<td>High-value purchasing / seller operations</td>
<td>Strong fit</td>
</tr>
<tr>
<td>Low</td>
<td>Basic order history / preferences</td>
<td>Weak fit</td>
</tr>
</table>
# 12. STRUCTURAL AMPLIFIERS
<table header-row="true">
<tr>
<td>Amplifier</td>
<td>Effect</td>
<td>Explanation</td>
</tr>
<tr>
<td>Physical-device control</td>
<td>Very high</td>
<td>Session compromise affects physical world</td>
</tr>
<tr>
<td>Money movement / payout control</td>
<td>Very high</td>
<td>Direct financial consequence</td>
</tr>
<tr>
<td>Health data</td>
<td>High</td>
<td>Sensitive information + regulatory/reputational consequences</td>
</tr>
<tr>
<td>Children's data</td>
<td>High</td>
<td>Sensitive population + regulatory exposure</td>
</tr>
<tr>
<td>Privileged business data</td>
<td>High</td>
<td>IP/customer-data/operational consequence</td>
</tr>
<tr>
<td>Drop/limited-release model</td>
<td>Medium-high</td>
<td>Account abuse can damage trust and revenue</td>
</tr>
<tr>
<td>High-ticket financing</td>
<td>Medium</td>
<td>High loss per event</td>
</tr>
<tr>
<td>Subscription</td>
<td>Medium</td>
<td>Persistent financial state</td>
</tr>
<tr>
<td>Age-gated commerce</td>
<td>Medium</td>
<td>Compliance/licensing risk</td>
</tr>
<tr>
<td>Practitioner portal</td>
<td>Medium</td>
<td>Channel integrity</td>
</tr>
<tr>
<td>Franchise/multi-location</td>
<td>Low-medium</td>
<td>More account surfaces</td>
</tr>
<tr>
<td>Creator/community trust</td>
<td>Low-medium</td>
<td>Primarily consequence/personalization</td>
</tr>
<tr>
<td>Made-in-USA</td>
<td>Context only</td>
<td>Useful messaging context, not core product fit</td>
</tr>
</table>
**Critical rule:** An attribute should become a permanent ICP amplifier only after evidence shows it predicts either session consequence or buying behavior.
# 13. NEGATIVE ICP
## Hard disqualifiers
- no meaningful authenticated session
- no meaningful post-login value
- no external users
## Strong commercial negatives
- very small company without sufficient commercial capacity
- large enterprise procurement incompatible with current self-serve motion
- corporate-owned with centralized procurement
- recent acquisition/integration that freezes vendor decisions
- founder/leadership transition that makes buyer routing unclear
These are primarily routing/commercial issues unless they eliminate the underlying product problem.
# 14. ICP VS ROUTING
This distinction is mandatory.
### ICP asks
> **Should Sentinel Layer care about this company?**
### Decision Makers asks
> **Who inside that company matters?**
### Buying Intent asks
> **Why act now?**
A company can be excellent ICP but poor current outreach priority.
# 15. ICP CLASSES
## ICP-A — Exceptional
- strong session privilege
- high consequence
- meaningful session volume
- commercially viable
- identifiable buyer
## ICP-B — Strong
- meaningful authenticated session
- moderate/high consequence
- good commercial fit
- no major negatives
## ICP-C — Conditional
- login exists
- some meaningful value exists
- consequence is limited or uncertain
- commercial fit is acceptable
## NON-ICP
- no meaningful login
- no meaningful post-login capability
- low-value account
- clearly incompatible commercial motion
# 16. ICP RESEARCH REQUIREMENTS
For each company establish:
### Identity
- company
- domain
- business model
- ownership
- employee range
### Session
- does login exist?
- what exists behind login?
- what actions can the user perform?
- is the session customer, employee, practitioner, admin, or device-linked?
### Consequence
- financial
- sensitive data
- privileged operation
- physical/device control
- reputation/community
- regulatory sensitivity
### Commercial
- employee count
- approximate scale
- revenue/funding where available
- organizational maturity
- procurement structure
### Technology
- application stack
- authentication system
- subscription/payment infrastructure
- connected devices
- relevant integrations
### Negative conditions
- centralized parent procurement
- acquisition/integration
- no buyer
- no meaningful session value
- enterprise-only sales motion
# 17. EVIDENCE STANDARD
### Strong evidence
- company website
- login/account page
- product documentation
- application/product description
- official company pages
- official filings
- reliable public company/employee information
- directly observed technology
- documented business model
### Weak evidence
- generic industry assumptions
- guessed traffic-to-fraud relationships
- inferred security maturity without evidence
- assuming every Shopify account has meaningful session value
### Rule
> **Do not infer session value merely because a login exists. Determine what the authenticated user can actually access or change.**
# 18. ICP SCORE
The ICP should not use a single flat score.
## A. Product Fit — 0–10
Measures:
- authenticated session
- session privilege
- session value
- consequence severity
- session volume
- relevant structural amplifiers
## B. Commercial Fit — 0–10
Measures:
- company size
- revenue/economic capacity
- organizational maturity
- implementation capability
- self-serve purchasing compatibility
- procurement complexity
## C. Reachability — 0–10
Measures:
- identifiable buyer
- direct contact path
- accessible decision maker
- organizational ownership
- ability to reach technical and economic stakeholders
## D. Buying Intent
Owned entirely by the separate Buying Intent model.
### Do not combine these into one number.
This preserves the distinction between:
> "They need us."
and:
> "They will buy now."
# 19. PRACTICAL ICP CLASSES
### Exceptional
High session privilege/consequence + strong commercial fit + identifiable buyer.
### Strong
Meaningful authenticated session + moderate/high consequence + good commercial fit.
### Conditional
Login/value exists but consequence or commercial fit is uncertain.
### Non-ICP
No meaningful session, no meaningful post-login capability, or incompatible motion.
# 20. OPERATING PRINCIPLE
The system should always ask these questions in order:
**1. Is there an authenticated session?**
If no → reject.
**2. What can that session access or change?**
If almost nothing → reject/deprioritize.
**3. What happens if the session is compromised?**
The more severe the consequence, the stronger the ICP.
**4. Can this company realistically buy?**
Evaluate size, maturity, economics, procurement, and buyer accessibility.
**5. Is this the right segment for our current GTM motion?**
E-commerce first; B2B software next.
**6. Is there a reason to act now?**
That belongs to Buying Intent, not ICP.
# 21. ONE-LINE ICP
> **A commercially viable company with externally authenticated user sessions that provide meaningful access, privilege, or control—especially financial, sensitive-data, administrative, or physical-device capabilities—where compromise of that session would create material business, security, privacy, financial, or safety consequences.**
### Current outbound sweet spot
> **US e-commerce/DTC companies, typically 50–500 employees and ≥100K monthly sessions/users, with customer accounts containing meaningful post-login value, where Sentinel Layer can be adopted through a \$99–\$499/month self-serve motion.**
# 22. RELATIONSHIP TO THE OTHER TWO DOCUMENTS
## ICP
**Which companies should Sentinel Layer care about?**
## Decision Makers
**Who inside those companies matters?**
## Buying Intent
**Why now?**
The three systems must not duplicate one another.
# 23. FINAL CANONICAL MODEL
**ICP = Product Fit + Commercial Fit + Reachability**
Where:
**Product Fit** = Authenticated Session × Session Privilege × Consequence × Scale
**Commercial Fit** = Ability to Buy × Ability to Implement × Procurement Compatibility
**Reachability** = Buyer Exists × Buyer Accessible × Organization Has Decision Authority
Then:
**Buying Intent** = Why Now
And:
**Decision Maker Selection** = Who to Contact
# 22. OBSERVED PAIN EVIDENCE
Public complaints, reviews, community posts, and company-specific security discussions can strengthen our understanding of consequence and personalization, but they are **not hard ICP gates**.
ICP qualification still requires evidence that:
- an authenticated session exists
- the session has meaningful post-login value or privilege
- compromise has meaningful consequences
- the company can realistically buy
Observed pain evidence is a separate layer.
### Examples
- “Someone accessed my account.”
- “My account was hacked.”
- “Unauthorized orders were placed.”
- “Someone changed my password/email.”
- repeated customer reports of suspicious account access
- company-specific fraud/security problems documented by a reliable source
### Classification
**Structural evidence** → determines ICP.
**Observed pain evidence** → strengthens consequence understanding and personalization.
**Buying-intent evidence** → explains why the company may act now.
### Review rule
Never upgrade a customer complaint into a confirmed company incident without independent corroboration.
For example:
> “A customer publicly reported unauthorized account access.”
is valid when that is what the source says.
> “The company suffered an account takeover incident.”
requires stronger independent evidence.
### Pain-evidence hierarchy
**Company-specific security evidence \> repeated company-specific complaints \> relevant category abuse \> generic security discussion.**
Generic negative sentiment must not be used as proof of SentinelLayer-relevant pain.
Personalization is governed by the canonical <mention-page url="https://app.notion.com/p/3ddb4f1d1069819bbb2ddb8fdef2426d"/>.