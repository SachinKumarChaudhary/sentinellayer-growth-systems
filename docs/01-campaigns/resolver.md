# Campaign Resolver

Campaign/Messaging owns this resolver. It selects a treatment but never performs delivery.

## Inputs

- campaign configuration
- frozen campaign/person context
- upstream priority
- versioned strategy, offer and sequence records
- optional running experiment and variants
- sequence steps

The resolver consumes the upstream priority. It does not recompute ICP, FIT, INTENT, or behavioral priority.

## Determinism

Experiment assignment uses SHA-256 of campaign_id + ":" + person_id and a stable 0–99.99 bucket. It does not use Python's process-randomized hash().

## Resolution

1. Validate priority.
2. Validate base versions.
3. Validate context/version identity.
4. Assign a running experiment deterministically.
5. Apply selected variant overrides.
6. Persist selected identifiers at enrollment.
7. Resolve the current step against the frozen sequence version.
8. Pass the result to the renderer.

No later strategy activation silently mutates existing enrollments.

## Boundary

Intelligence -> priority -> Campaign Resolver -> Treatment Renderer -> RenderedSendTreatment -> Mail Engine

## Fail closed

Unknown priority, unusable versions, context mismatch, invalid experiment state/allocation, duplicate active steps, or missing steps stop resolution.
