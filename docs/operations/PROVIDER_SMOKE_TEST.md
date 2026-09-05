# Controlled Provider Smoke Test

This test is intentionally separate from normal CI because it can send real email and requires provider credentials.

## GitHub environment

Create a protected environment named `staging-mail` and store only the staging credentials there. GitHub environment protection should require approval before the workflow can access those secrets.

Required environment secrets:

- `SUPABASE_DATABASE_URL`
- `SL_SMTP_HOST`
- `SL_SMTP_PORT`
- `SL_SMTP_USERNAME`
- `SL_SMTP_PASSWORD`
- `SL_IMAP_HOST`
- `SL_IMAP_PORT`
- `SL_IMAP_USERNAME`
- `SL_IMAP_PASSWORD`
- `SL_IMAP_MAILBOX`
- `SL_STAGING_RECIPIENT`

Do not put these values in the repository or workflow YAML.

## Preconditions

- Dedicated staging sender mailbox.
- DNS records verified for the sending domain: SPF, DKIM, and DMARC.
- Staging recipient is explicitly allowlisted.
- `SL_REAL_EMAIL_ENABLED=true` is used only inside the protected staging job.
- Normal CI continues to use `SL_REAL_EMAIL_ENABLED=false`.

## Test sequence

1. Verify SMTP authentication without sending to an arbitrary address.
2. Create one controlled campaign send for the allowlisted recipient.
3. Confirm the exact rendered payload persisted before SMTP handoff.
4. Send exactly one message.
5. Reply from the recipient mailbox.
6. Poll IMAP and process the inbound message.
7. Verify thread correlation and inbound persistence.
8. Verify an interested/question reply reaches the sales bridge.
9. Verify a negative/unsubscribe reply stops future sends and creates suppression where applicable.
10. Verify duplicate inbound delivery is idempotent.
11. Record timestamps, provider response classification, and final database state without recording message contents or credentials in CI logs.

## Failure rule

Any unexpected recipient, missing environment secret, disabled safety control, provider authentication failure, thread mismatch, duplicate side effect, or suppression failure is a hard test failure. The workflow must never fall back to an arbitrary recipient or broaden the send scope.
