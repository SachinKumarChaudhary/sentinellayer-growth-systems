# Campaign execution orchestration

The executable Campaign path is now:

1. Claim one due enrollment step with a short database lease.
2. Build a RenderContext from the canonical claimed snapshot.
3. Render and validate an immutable RenderedSendTreatment.
4. Convert it to a validated SendRequest.
5. Return the request to Mail; Campaign never performs delivery.
6. On any rendering/handoff failure, release the lease so the step can be retried safely.

This preserves campaign/version provenance and prevents two workers from rendering the same sequence step simultaneously.
