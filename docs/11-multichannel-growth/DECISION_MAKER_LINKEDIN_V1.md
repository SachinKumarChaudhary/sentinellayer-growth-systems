# Decision-Maker + LinkedIn Resolution v1

## Objective
Produce outreach-ready decision makers with a current-company match and a canonical LinkedIn profile URL. Precision is preferred to filling missing fields.

## Pipeline
1. Determine buyer roles from company size and available signals.
2. Discover candidates through independent public sources.
3. Normalize LinkedIn profile URLs.
4. Resolve person-to-company identity using name, company, title, company-site evidence, and independent corroboration.
5. Penalize former/stale employment and ambiguous identity.
6. Promote only high-confidence candidates to outreach-ready status.
7. Preserve source URLs and source types for auditability.

## Important boundary
LinkedIn is a contact surface, not the system of record. Public search/discovery may identify a LinkedIn profile, but the system must not assume that a URL proves current employment. Evidence and freshness are evaluated separately.

## Initial operational thresholds
- `outreach_ready`: confidence >= 0.90, LinkedIn profile resolved, current-employer confidence >= 0.75.
- `strong_candidate`: confidence >= 0.75, LinkedIn profile resolved, current-employer confidence >= 0.75.
- `review`: everything else.

These are initial transparent thresholds for calibration, not permanent statistical claims.

## Evidence contract
The decision-maker playbook remains authoritative: raw research must not self-assign verification labels; URLs must correspond to sources actually observed/fetched in the enrichment session; missing evidence is preferable to fabrication. Decision-maker contact methods remain attached to the person.
