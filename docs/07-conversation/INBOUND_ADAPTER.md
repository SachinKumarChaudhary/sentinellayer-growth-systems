# Inbound provider adapter

The inbound boundary accepts a provider-neutral message envelope and requires provider_message_id, sender email, thread_key, account_id, and person_id before classification. It normalizes provider headers without granting the provider access to suppression or sales mutations.

Provider adapters should translate IMAP/API/webhook payloads into this envelope. Duplicate provider_message_id values are rejected by the durable database unique constraint.
