# Self-Hosted Deployment

## Deployment

Use `scripts/selfhosted/deploy.sh`.

Required inputs are external to Git:
- `.env`
- database credentials
- provider credentials
- tracking hash secret
- any production-only configuration

The deployment script validates Compose before starting services. It never enables real email implicitly.

## Rollback

Use `scripts/selfhosted/rollback.sh` with an explicit known-good release tag.

Rollback always forces `SL_REAL_EMAIL_ENABLED=false`. Durable Mail state must be reconciled before outbound execution resumes.

## Required checks

After deployment or rollback:
- inspect container health;
- verify Tracking `/healthz` and `/readyz` through the edge when enabled;
- verify Mail worker readiness;
- verify logs contain no credentials/tokens;
- verify release/version identity;
- run synthetic smoke checks;
- only then consider the production gate.

These scripts are runtime mechanics. They do not decide Campaign, Mail, or Tracking business policy.
