# Campaign → Mail Handoff

## Ownership
Campaign owns treatment selection and rendering. Mail owns send persistence, claiming, delivery, retry, ambiguous outcomes, provider integration, and final send state.

## Adapter contract
`CampaignMailHandoff.build_send_request()` accepts a validated `RenderedSendTreatment` plus `mailbox_id` and `scheduled_at`. It validates both shared contracts and returns a `SendRequest`. It never connects to SMTP or mutates Mail send state.

## Idempotency
Default key:

`campaign-send:{campaign_id}:{person_id}:{sequence_step_id}`

An explicit key may be supplied when the agreed orchestration layer has a stronger generation identifier. The key must remain stable across retries of the same business send.

## Safety
- Rendered treatment is revalidated at the boundary.
- Recipient comes from the frozen treatment; Campaign does not rewrite it during handoff.
- Mailbox ID must be a UUID.
- Schedule must be timezone-aware.
- Send ID is a UUID.
- Invalid requests fail closed.

## Progression rule
Campaign step completion must occur only after the Mail orchestration boundary has safely accepted ownership. Provider acceptance is not a prerequisite for Campaign handoff completion; Mail owns provider outcome state.

## Not implemented here
This adapter does not create a Mail `send` row or call the SMTP/provider engine. Those are Mail-owned operations and require the Mail session's current implementation/contract.
