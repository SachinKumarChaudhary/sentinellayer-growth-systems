# Campaign Renderer

The renderer converts a resolved, versioned treatment into the immutable `RenderedSendTreatment` contract. It never sends mail.

## Safety invariants

- Message and CTA versions must be reviewable, testing, or active.
- Message content must be QA approved.
- Required evidence must exist.
- Every personalization placeholder must resolve.
- Recipient identity comes from the frozen enrollment context.
- Rendering does not perform SMTP, queue claiming, retries, suppression, or delivery.
- Output is validated against `schemas/rendered-send-treatment.schema.json`.
- Exact version identifiers are retained for attribution.

## Flow

```
resolved treatment
      |
version/status checks
      |
evidence validation
      |
personalization + CTA rendering
      |
contract validation
      |
RenderedSendTreatment
      |
existing mail engine
```

## Non-goals

The renderer does not invent evidence, choose recipients, select campaigns, assign experiments, enforce provider limits, decide suppression, promote experiments, or send mail.
