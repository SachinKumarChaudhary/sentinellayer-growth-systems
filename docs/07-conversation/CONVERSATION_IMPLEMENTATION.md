# Conversation Intelligence — V1 Runtime

## Ownership

Conversation owns inbound reply normalization, thread association, deterministic classification, conversation state, and ConversationHandoff production.

It does not send mail, mutate suppression state directly, or create sales opportunities.

## Runtime path

Inbound provider message → normalization → thread key → classification → recommended action → validated ConversationHandoff.

Explicit unsubscribe and negative signals are deterministic safety signals. The policy-owning boundary executes irreversible suppression.

## Persistence

Supabase/PostgreSQL stores conversation threads and replies. provider_message_id is unique to prevent duplicate inbound effects.

## AI boundary

Hermes may later enrich classification, extraction, or response suggestions. Its result must remain schema-validated and cannot bypass deterministic safety rules.

## Remaining integration gates

- inbound provider adapter (IMAP/API/webhook)
- provider thread-header normalization
- suppression/reply-stop integration with Mail/Campaign
- Mail → Conversation correlation
- staging inbound mailbox test
- synthetic Campaign → Mail → Tracking → Conversation test
