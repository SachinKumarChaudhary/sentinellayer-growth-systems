# Purpose
Turn verified evidence into specific, non-fictional outreach angles.
# Core rule
Every personalization claim must trace to current evidence. Do not manufacture familiarity, motives, undocumented events, incidents, or internal company conditions.
# Position in the lead-generation system
**ICP Fit → Buyer Route → Buying Intent → Negatives → Behavior → Priority → Personalization → Outreach**
Personalization is a reasoning/synthesis layer, not a replacement for ICP classification or buying-intent scoring.
- **ICP** answers: Should SentinelLayer care about this company?
- **Decision Makers** answers: Who owns the relevant problem, risk, implementation, budget, or consequence?
- **Buying Intent** answers: Why act now?
- **Personalization** answers: What verified evidence should shape what we say to this buyer?
# Outputs
Every personalization result should produce:
- evidence-backed angle
- buyer-specific angle
- source reference(s)
- evidence date
- confidence
- limitations / uncertainty
- message constraints
- QA status
# 1. PERSONALIZATION EVIDENCE TAXONOMY
## P1 — Company-specific security or fraud pain
Highest-value external personalization.
Examples:
- customer publicly reports an account takeover
- unauthorized account access
- suspicious login
- unauthorized purchase after account compromise
- payout/account manipulation
- security failure affecting authenticated accounts
- company-specific fraud/security problem documented by a reliable source
Rule:
> Use the exact observed claim. Do not upgrade a customer report into a confirmed company incident unless independently corroborated.
## P2 — Repeated customer security complaints
Multiple independent recent complaints describing materially similar security/account problems.
Examples:
- several customers reporting hacked accounts
- repeated unauthorized-order/account-access complaints
- repeated security/privacy complaints tied to the authenticated product
Use:
- strong personalization evidence
- possible intent corroboration
- not automatically a buying-intent trigger
## P3 — Vendor / competitor dissatisfaction
Evidence that the company or its users are dissatisfied with an existing security/fraud solution or evaluating alternatives.
Examples:
- named vendor coverage complaint
- false-positive complaint
- pricing/contract complaint
- missing capability
- support/reactivity complaint
- explicit comparison or alternative search
Use:
- personalization
- possible switching/evaluation intent
- route to the buyer who owns the affected capability
## P4 — Relevant community / dark-funnel evidence
Company-specific or highly relevant conversations from Reddit, forums, developer communities, security communities, public social discussion, or public customer complaint surfaces.
Hierarchy:
**company-specific incident \> repeated company-specific complaint \> credible category-specific abuse \> generic category discussion**
Generic category discussion must never be rewritten as company-specific pain.
## P5 — First-party product behavior
Examples:
- pricing-page engagement
- docs engagement
- trial signup
- integration/evaluation activity
- /evaluate activity
- SDK installation
- multiple stakeholders engaging from one account
- positive reply / explicit information request
First-party behavior is generally stronger evidence than third-party inference because the prospect self-identifies as researching SentinelLayer.
## P6 — Organizational / technical triggers
Examples:
- security/fraud hiring
- relevant executive change
- replatforming / architecture migration
- authenticated product launch
- new market entry
- funding
- expansion
These are useful personalization context and may also contribute to Buying Intent under the canonical intent policy.
## P7 — Contextual / quantified evidence
Examples:
- VAMP quantified risk context
- traffic scale
- seasonality
- business model
- product scale
Use as supporting context, not as a substitute for actual pain evidence.
# 2. PAIN EVIDENCE ≠ BUYING INTENT
A public complaint may prove that a relevant problem has been observed without proving that the company is currently shopping for a solution.
Example:
**Single old review**
> “Someone hacked my account.”
Classification:
- pain evidence: yes
- personalization: yes
- current intent: unknown
**Three recent independent complaints + security hiring + replatform**
- pain evidence: strong
- personalization: strong
- intent: stronger because independent signal families corroborate
The system must preserve this distinction.
# 3. SECURITY / NEGATIVE-REVIEW POLICY
A negative review becomes relevant only when it is:
- company-specific
- security/fraud/account related
- materially relevant to authenticated-session risk
- current enough to matter
- attributable to an actual observed experience
Do not treat these as security evidence:
- generic “bad company” sentiment
- shipping complaints
- customer-service complaints with no security consequence
- vague statements such as “their security is terrible”
- unrelated payment UX complaints
- complaints about another company
- speculation about an incident
- duplicated copies of one original complaint
## Review interpretation rule
When a customer says:
> “My account was hacked.”
Outbound wording should remain:
> “A customer publicly reported unauthorized account access…”
not:
> “You had an account takeover.”
The latter requires independent corroboration.
# 4. REVIEW EVIDENCE STRENGTH
### Strong
Specific, recent, company-specific report involving authenticated-session security and a concrete consequence.
### Moderate
Several recent independent complaints describing similar account/security problems.
### Weak
Generic security dissatisfaction without a concrete event.
### Irrelevant
Negative sentiment unrelated to post-login security.
Additional corroboration increases confidence but does not allow unsupported claims.
# 5. SOURCE HIERARCHY
Prefer, in order:
1. Direct company-specific evidence
2. Repeated company-specific customer complaints
3. Named vendor dissatisfaction / evaluation evidence
4. Relevant community discussion
5. Category-level discussion
6. Generic contextual evidence
Provider count is not evidence count. Multiple copies of the same article/review do not become independent corroboration.
# 6. BUYER-SPECIFIC PERSONALIZATION
The same evidence should produce different angles depending on the contacted buyer.
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
<td>integration / session instrumentation</td>
<td>selective step-up without broad UX friction</td>
<td>loss / operational exposure</td>
<td>repeat hacked-account workload</td>
</tr>
<tr>
<td>Unauthorized transaction</td>
<td>fraud/session abuse</td>
<td>request-level controls</td>
<td>safer checkout/account actions</td>
<td>direct financial leakage</td>
<td>dispute/support volume</td>
</tr>
<tr>
<td>Account lockout complaint</td>
<td>distinguish attack from legitimate user</td>
<td>auth/session telemetry</td>
<td>reduce unnecessary friction</td>
<td>support cost</td>
<td>ticket volume</td>
</tr>
<tr>
<td>Privacy complaint</td>
<td>sensitive-session protection</td>
<td>implementation / data path</td>
<td>trust and UX</td>
<td>exposure cost</td>
<td>customer trust</td>
</tr>
<tr>
<td>Vendor dissatisfaction</td>
<td>capability gap</td>
<td>stack replacement / augmentation</td>
<td>product impact</td>
<td>cost / ROI</td>
<td>operational coverage</td>
</tr>
</table>
Support/CX is generally evidence/champion territory, not automatically the economic buyer.
# 7. PERSONALIZATION TOKEN HIERARCHY
Choose the strongest supported reason available:
1. Explicit company-specific security/fraud pain
2. Repeated company-specific security complaints
3. Active security/compliance project
4. Vendor/competitor dissatisfaction or evaluation
5. Strong first-party product behavior
6. Security/fraud hiring
7. Relevant executive change
8. Architecture/replatforming
9. Authenticated product launch / expansion
10. Funding
11. Seasonal exposure
12. Quantified risk/context
13. Generic product value
Do not skip to a weaker generic hook when stronger supported evidence exists.
# 8. CONFIDENCE / CLAIM TYPES
Each personalization result should identify:
- **OBSERVED** — directly supported by a source
- **CORROBORATED** — supported by multiple independent sources
- **INFERRED** — reasonable synthesis that must not be written as a fact
- **CONTEXT** — useful background, not evidence of pain
Outbound copy should present OBSERVED and CORROBORATED information as factual. INFERRED material must be framed cautiously or excluded.
# 9. PERSONALIZATION RECORD
Recommended internal fields:
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
# 10. MESSAGE CONSTRAINTS
Every personalization angle must answer:
- What exactly was observed?
- Why is it relevant to the buyer?
- Why is it relevant to SentinelLayer?
- What part is fact versus inference?
- What must not be claimed?
Never manufacture:
- familiarity
- motives
- urgency
- internal security posture
- confirmed incidents
- vendor dissatisfaction
- budget
- planned projects
# 11. VAMP POLICY
VAMP is a fallback quantified-context token.
Use it when stronger evidence is absent.
Do not allow VAMP to outrank actual security pain, customer security complaints, vendor dissatisfaction, first-party evaluation, or explicit company-specific incidents.
VAMP supports personalization; it does not prove buying intent.
# 12. PERSONALIZATION QA
Before outreach:
- [ ] source exists and resolves
- [ ] evidence actually supports the claim
- [ ] evidence is current enough for the intended use
- [ ] duplicate sources are not treated as independent
- [ ] customer complaint is not upgraded into a confirmed incident
- [ ] pain evidence is not mislabeled as buying intent
- [ ] buyer angle matches the owner's problem
- [ ] inference is separated from observation
- [ ] no generic complaint is presented as company-specific
- [ ] message does not imply familiarity that has not been earned
# 13. RELATION TO THE CORE DOCUMENTS
The canonical three-document system remains:
**ICP** → Should SentinelLayer care about this company?
**Decision Makers** → Who can move the purchase forward?
**Buying Intent** → Why act now?
This page adds:
**Personalization** → What verified evidence should shape what we say?
Reference:
<mention-page url="https://app.notion.com/p/3dcb4f1d106981549f14e847a99fa2bf"/>
# 14. STATUS
Canonical personalization policy for the SentinelLayer Growth System.