# TinyFish MVP Query Catalog

These are query families, not mandatory calls. The research controller chooses only the queries needed for the company and current evidence gaps.

## 1. Company identity
- `"{brand}" company`
- `"{domain}" company`
- `"{brand}" parent company`
- `"{brand}" owned by`
- `"{brand}" subsidiary`
- `"{brand}" acquisition`
- `"{brand}" leadership`

Purpose: resolve operating entity, parent, ownership, and corporate routing before researching people.

## 2. Firmographics / ICP
- `"{brand}" employees`
- `"{brand}" company size`
- `"{brand}" employees LinkedIn`
- `"{brand}" traffic`
- `"{brand}" monthly visits`
- `"{brand}" business model`

Use these as corroboration for the source-of-record company fields, not as automatic replacement of structured data.

## 3. Login / session surface
- `site:{domain}/login`
- `site:{domain}/account`
- `site:{domain}/account/login`
- `site:{domain}/register`
- `"{brand}" customer login`
- `"{brand}" customer account`

Then TinyFish Fetch discovered/login URLs. Look for orders, addresses, subscriptions, loyalty, payment information, personal data, financing, device controls, or other valuable session data.

## 4. A1 — payout/admin takeover/fraud pain
- `site:reddit.com/r/shopify "{brand}" payout`
- `site:reddit.com "{brand}" chargeback`
- `site:reddit.com "{brand}" fraud`
- `site:reddit.com "{brand}" account takeover`
- `site:reddit.com "{brand}" bot`
- `"{brand}" payout bank account changed`
- `"{brand}" admin account taken over`
- `"{brand}" session hijacking`

Record dated source evidence or `none found`.

## 5. A2 — technology / login
- `"{brand}" Shopify Plus`
- `"{brand}" Shopify`
- `"{brand}" customer account`
- `"{brand}" authentication`
- `"{brand}" Recharge`
- `"{brand}" Skio`
- `"{brand}" membership`
- `"{brand}" loyalty`

Prefer the company's own site and fetched pages for actual login/session facts. Do not infer product stack from a single keyword collision.

## 6. A3 — security/compliance/hiring
- `"{brand}" SOC 2`
- `"{brand}" ISO 27001`
- `"{brand}" PCI DSS`
- `"{brand}" security engineer`
- `"{brand}" information security`
- `"{brand}" fraud analyst`
- `"{brand}" risk analyst`
- `"{brand}" trust and safety`
- `site:greenhouse.io "{brand}" security`
- `site:lever.co "{brand}" security`

## 7. A4 — competitor / security tooling
- `"{brand}" Sift`
- `"{brand}" SEON`
- `"{brand}" Forter`
- `"{brand}" Kount`
- `"{brand}" Signifyd`
- `"{brand}" Castle`
- `"{brand}" Arkose`
- `"{brand}" Riskified`
- `"{brand}" DataDome`

Require company-specific evidence. Do not classify generic industry comparison pages as the company's current vendor.

## 8. A5 — India bridge
For US leads, normally record `none — US lead` unless the decision-maker playbook calls for a bridge check. When useful:
- `"{founder}" India`
- `"{founder}" Indian`
- `"{brand}" Bengaluru`
- `"{brand}" India engineering`

## 9. A6 — funding / hiring / expansion
- `"{brand}" funding`
- `"{brand}" raised`
- `"{brand}" acquisition`
- `"{brand}" expansion`
- `"{brand}" new market`
- `"{brand}" new CEO`
- `"{brand}" new CTO`
- `"{brand}" hiring`
- `"{brand}" careers`

Every positive dated event gets `signal_date`, source URL, and evidence.

## 10. Decision-maker discovery
Search only roles selected by the buyer-role planner.

### Security
- `site:linkedin.com/in "{brand}" CISO`
- `site:linkedin.com/in "{brand}" "Head of Security"`
- `site:linkedin.com/in "{brand}" "Information Security"`

### CTO / engineering
- `site:linkedin.com/in "{brand}" CTO`
- `site:linkedin.com/in "{brand}" "Chief Technology Officer"`
- `site:linkedin.com/in "{brand}" "VP Engineering"`
- `site:linkedin.com/in "{brand}" "Head of Engineering"`

### Founder / CEO
- `site:linkedin.com/in "{brand}" founder`
- `site:linkedin.com/in "{brand}" CEO`
- `site:linkedin.com/in "{brand}" "Chief Executive Officer"`

### COO / finance
- `site:linkedin.com/in "{brand}" COO`
- `site:linkedin.com/in "{brand}" "Chief Operating Officer"`
- `site:linkedin.com/in "{brand}" CFO`
- `site:linkedin.com/in "{brand}" "VP Finance"`

### Ecommerce / digital
- `site:linkedin.com/in "{brand}" ecommerce`
- `site:linkedin.com/in "{brand}" "Head of Ecommerce"`
- `site:linkedin.com/in "{brand}" "Director of Ecommerce"`
- `site:linkedin.com/in "{brand}" "Head of Digital"`

## 11. Person identity / currentness corroboration
For each selected candidate:
- `"{person}" "{brand}"`
- `"{person}" "{brand}" "{title}"`
- `"{person}" "{brand}" current`
- `"{person}" "{brand}" 2026`
- `site:{domain} "{person}"`
- `"{person}" "{brand}" announcement`

Purpose: establish same-person identity, current company relationship, title, and temporal evidence. Name similarity alone is insufficient.

## 12. Public contact discovery
Only after identity is sufficiently resolved:
- `"{person}" "{brand}" email`
- `"{person}" "{domain}" email`
- `site:{domain} "{person}"`
- `"{person}" "{brand}" phone`

Observed public addresses remain observed evidence. Pattern-derived emails are candidates until independently verified.

## Fetch targets
Use TinyFish Fetch for selected URLs such as:
- company homepage/about/team/leadership
- login/account/register pages
- security/privacy/compliance pages
- relevant careers/job pages
- authoritative person/company profiles
- press releases and dated announcements
- public contact/about pages

Do not blindly fetch every URL from Search. Rank and select useful sources, deduplicate, and cache.

## Required research output discipline
The agent returns raw evidence only. It must not write `VERIFIED`, `INFERRED`, or `NOT_FOUND` tags into evidence fields. Deterministic validation assigns those tags.

Every cited URL must be returned by TinyFish Search or actually fetched during the current research run. Empty beats fabricated.
