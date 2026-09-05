# staging-mail GitHub Environment

Required secrets:

- SL_SMTP_HOST
- SL_SMTP_PORT
- SL_SMTP_USERNAME
- SL_SMTP_PASSWORD
- SL_IMAP_HOST
- SL_IMAP_PORT
- SL_IMAP_USERNAME
- SL_IMAP_PASSWORD
- SL_IMAP_MAILBOX

The environment must have manual approval/protection enabled before the smoke workflow can access these secrets.

The workflow is deliberately separate from normal CI. It performs provider authentication first and sends only when the workflow input explicitly enables the controlled test message.
