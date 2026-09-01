# System Handoff Protocol

Every handoff specifies producer, consumer, contract, identifiers, schema version, lifecycle/state, error behavior, idempotency expectations, security/RLS expectations, and a boundary test.

## Campaign → Mail
Campaign provides a fully resolved, version-pinned treatment. Mail validates and executes it. Mail does not resolve campaign strategy.

## Mail → Tracking / Conversation
ProviderOutcome and canonical event envelope preserve send identity, provider identity, attempt identity, timestamps, and outcome classification.

## Tracking → Conversation
TrackingEvent provides normalized behavioral evidence. Conversation determines meaning; tracking does not directly declare a sales outcome.

## Conversation → Sales
ConversationHandoff provides classified conversation state and evidence. Sales determines commercial workflow state.

## Operational outcomes → Analytics
Analytics derives attribution and metrics from canonical source events/outcomes and does not become operational source of truth.

## Agent handoff
Commit implementation, contract/schema changes, tests, documentation, changed interfaces, migrations, unresolved risks, and the receiving agent's next action. The receiver fetches current repository state before modifying it.
