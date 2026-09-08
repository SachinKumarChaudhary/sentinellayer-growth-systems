# Small-Batch AI Enrichment Research Packet

Use this prompt with ChatGPT, Gemini, Claude, Grok, or DeepSeek when enriching **1–3 companies at a time**.

## Objective

Research only public, accessible information. Return evidence-backed structured data for the supplied company IDs.

The output is an enrichment packet, not a marketing summary.

## Required rules

- Never invent a person, email, phone, URL, company fact, or buying-intent event.
- Do not write the labels VERIFIED, INFERRED, or NOT_FOUND; validation assigns those states.
- Every factual claim that depends on a web source must include the URL actually consulted.
- Keep a claim even when it is negative or unavailable only where the playbook requires a signal field; do not fabricate a substitute.
- Email addresses discovered by pattern are candidates until separately verified.
- Generic company emails belong in company_contacts, not decision_makers.
- Use the Decision Makers Playbook for role selection.
- Use Buying Intent Classification v2.1 / Lead Classification Playbook for A1–A6 signals, dates, weights and routing context.
- Do not calculate a final behavioral override from third-party research. First-party behavior is system-owned.
- Prefer evidence quality over completeness.

## Input

Provide 1–3 records:

```json
{
  "companies": [
    {
      "company_id": 123,
      "domain": "example.com",
      "name": "Example",
      "country": "US",
      "city": "Austin",
      "known_employee_count": 180,
      "known_visits": 800000,
      "known_website": "https://example.com",
      "known_company_linkedin": "https://linkedin.com/company/example"
    }
  ]
}
```

## Research order

### Company

Research the company before selecting people:

- employee/scale evidence
- traffic/app scale when publicly available
- vertical/business model
- ownership/parent company
- customer login surface
- sensitive data/session value
- IoT/device control
- subscriptions
- compliance/SOC 2/ISO exposure
- recent company events
- public company contacts
- public social profiles

### Decision makers

Use the company attributes plus the Decision Makers Playbook to choose the roles to hunt.

Normally find at least two strong candidates when evidence exists.

For every decision maker collect:

- full name
- title
- role family
- why relevant
- public LinkedIn URL if actually found
- public Instagram/Reddit/X/other social when useful
- public email candidate(s)
- public phone when available
- source evidence

### Buying intent

Research all applicable A1–A6 signals:

- A1 payout / admin takeover / session hijack / chargeback / scalping
- A2 technology/login surface/replatforming
- A3 compliance/security/fraud hiring
- A4 competitor security/fraud tooling
- A5 India connection
- A6 funding/growth/executive changes

For every dated trigger record the actual event date and source.

Do not turn a generic company attribute into an intent signal unless the playbook explicitly defines it as ongoing intent.

## Output

Return **JSON only**, matching:

```json
{
  "schema_version": "1.0",
  "packets": [
    {
      "schema_version": "1.0",
      "company_id": 123,
      "domain": "example.com",
      "merchant_name": "Example",
      "company_facts": {
        "employee_count": 180,
        "monthly_sessions": 800000,
        "has_login": true,
        "vertical": "DTC",
        "ownership_type": "founder_owned",
        "india_bridge": false,
        "data_sensitivity": "financial"
      },
      "company_contacts": [],
      "decision_makers": [],
      "intent_signals": [],
      "personalization_angle": null,
      "research_notes": []
    }
  ]
}
```

The system accepts a maximum of three packets per import.
