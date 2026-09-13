# Sentinel Layer — TinyFish-only MVP Enrichment

**Status:** Canonical MVP implementation plan  
**Date:** 2026-09-13

## Provider decision

For the MVP, TinyFish Search + TinyFish Fetch are the only web-research providers. Jina, Firecrawl, Exa, Tavily, browser automation, and other web research providers are deferred.

This matches the canonical decision log: TinyFish Search + Fetch is the primary web research/enrichment mechanism; cache results and avoid redundant re-fetches. The company is the ICP/root object and decision makers are the actionable outreach identities.

## Pipeline

`company -> company resolution -> company facts/ICP -> login/session -> A1-A6 intent -> buyer-role plan -> decision-maker discovery -> identity/currentness validation -> LinkedIn/contact enrichment -> evidence validation -> FIT/INTENT/BEHAVIOR -> P1-P4 -> campaign-ready`

## TinyFish responsibilities

### Search
Use TinyFish Search for:
- company identity / parent ownership
- leadership and buyer discovery
- security/fraud pain
- technology/login clues
- compliance/hiring
- competitor/risk tooling
- funding/growth/expansion
- person identity/currentness corroboration
- public contact discovery

### Fetch
Use TinyFish Fetch for the URLs selected from Search and known company URLs. Fetch team/leadership pages, about pages, login/account pages, security/compliance pages, relevant job pages, public announcements, and person evidence pages.

Do not use browser automation for the MVP.

## Research controller

Do not run every possible query for every company. The controller should:
1. resolve company identity;
2. qualify ICP and login/session surface;
3. if viable, run the A1-A6 intent families;
4. create the buyer-role plan from company context;
5. search for only the planned roles;
6. validate the strongest candidate identities;
7. fetch supporting evidence only for selected candidates/signals;
8. run targeted follow-up research only where evidence conflicts or is incomplete.

## Buyer role planning

Follow the Decision Makers Playbook:
- CISO/Head of Security first when one exists;
- otherwise CTO/VP Engineering;
- <150 employees: Founder/CEO is a primary economic buyer;
- 150-500 employees: COO/CFOO + CTO co-pair;
- corporate/PE owned: parent operating partner, otherwise ecommerce/local CTO;
- subscription: add Finance/Payments;
- health/kids/age-gated: add Legal;
- IoT: add Product/IoT.

Normally return at least two strong buyers when evidence exists. The system may discover more, but campaign enrollment should initially prioritize the best two threads.

## Person identity contract

A decision-maker candidate is not accepted merely because a search result contains a name/title.

Identity evidence should establish:
- exact person name;
- company relationship;
- current role/title;
- currentness/date evidence where available;
- LinkedIn/profile anchor when available;
- absence of an obvious homonym conflict.

Research agents emit raw evidence only. They must not write `VERIFIED`, `INFERRED`, or `NOT_FOUND`; deterministic validation assigns those states.

Every cited URL must be one actually fetched or returned by the current TinyFish research run. Empty or unresolved is preferable to fabricated evidence.

## LinkedIn

LinkedIn is the primary outreach surface for MVP. Preserve exact discovered URLs and supporting evidence. A LinkedIn URL alone is not sufficient to prove current employment; use company-side or independent corroboration where needed.

## Contacts

Person contact methods belong to the decision-maker record. Generic company contacts are separate.

Pattern-derived emails remain candidates until verified. Never turn masked emails, provider guesses, or inferred patterns into observed/verified addresses.

Run free evidence/oracles before paid verification. Preserve source and verification provenance.

## Evidence

Every factual claim should preserve:
- claim type/data;
- source URL;
- source type;
- observed timestamp;
- event date when relevant;
- confidence;
- evidence hash.

Company-level intent and person-level evidence are separate objects.

## Campaign-ready gate

A company can enter a campaign only when:
- company identity is resolved;
- ICP qualification is resolved;
- login/session surface is resolved;
- A1-A6 intent research is complete or explicitly `none found`;
- buyer roles are planned;
- selected decision makers have sufficient identity/currentness evidence;
- LinkedIn/contact state is usable for the intended outreach channel;
- no critical evidence/homonym errors remain;
- FIT and INTENT are scored deterministically;
- priority is computed;
- suppression rules pass.

## Observability

Track at least:
- searches requested/succeeded/failed;
- fetch URLs requested/succeeded/failed;
- cached/reused research;
- decision-maker candidates per company;
- identity validation pass/fail;
- LinkedIn coverage;
- usable contact coverage;
- evidence quality failures;
- intent signals found;
- FIT/INTENT/P1-P4 distribution;
- campaign-ready rate;
- provider/rate-limit errors;
- enrichment latency.

## Future provider insertion point

Jina may later be introduced behind a provider-neutral `research_page(url, purpose, importance)` abstraction. Do not build the Jina path into the MVP implementation now. The MVP must remain TinyFish-only.
