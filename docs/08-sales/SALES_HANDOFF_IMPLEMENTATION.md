# Sales handoff v1

Sales owns human follow-up tasks. Conversation provides evidence and a recommended action; Sales persists a durable task and does not autonomously send mail.

The handoff preserves account/person identity plus the trigger, priority, latest reply, behavioral summary, campaign context, and conversation summary.

Duplicate open tasks for the same account/person/trigger are prevented by a partial unique index.

## Boundary
Conversation → validated SalesHandoff → Sales task → human owner → outcome.

No LLM or inbound provider is allowed to mutate opportunity state directly.
