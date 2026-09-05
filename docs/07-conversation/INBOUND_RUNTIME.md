# Inbound mailbox runtime

The inbound path is now layered as:

IMAP mailbox -> ImapInboundProvider -> normalized inbound message -> ConversationRuntime -> durable Conversation -> Sales.

The provider adapter uses TLS IMAP on port 993, extracts Message-ID, thread headers, sender, body and the outbound X-SL-Send-Id correlation header, and only marks a message Seen after successful runtime handling.

Account/person identity resolution is injected through InboundIdentityResolver. This keeps mailbox transport separate from canonical identity state and allows a future Gmail/Graph adapter without changing Conversation.

Real mailbox credentials, provider routing, and DNS/mailbox validation remain deployment gates; no credential is stored in source control and the default outbound gate remains disabled.
