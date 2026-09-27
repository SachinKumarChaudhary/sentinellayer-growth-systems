-- Phase 2 provider-attempt observability contract.
-- Align durable attempt records with the canonical Provider Execution & Resilience Contract.

ALTER TABLE growth.entity_resolution_provider_attempts
    ADD COLUMN IF NOT EXISTS lead_id text,
    ADD COLUMN IF NOT EXISTS http_status integer,
    ADD COLUMN IF NOT EXISTS retry_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quota_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS raw_artifact_ref text,
    ADD COLUMN IF NOT EXISTS raw_artifact_hash char(64),
    ADD COLUMN IF NOT EXISTS evidence_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS escalation_reason text,
    ADD COLUMN IF NOT EXISTS information_gain_estimate numeric;

ALTER TABLE growth.entity_resolution_provider_attempts
    ADD CONSTRAINT entity_resolution_provider_attempts_retry_count_nonnegative
        CHECK (retry_count >= 0),
    ADD CONSTRAINT entity_resolution_provider_attempts_quota_state_object
        CHECK (jsonb_typeof(quota_state) = 'object'),
    ADD CONSTRAINT entity_resolution_provider_attempts_evidence_ids_array
        CHECK (jsonb_typeof(evidence_ids) = 'array'),
    ADD CONSTRAINT entity_resolution_provider_attempts_http_status_valid
        CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
    ADD CONSTRAINT entity_resolution_provider_attempts_raw_artifact_hash_format
        CHECK (raw_artifact_hash IS NULL OR raw_artifact_hash ~ '^[0-9a-f]{64}$');

CREATE INDEX IF NOT EXISTS entity_resolution_provider_attempts_lead_idx
    ON growth.entity_resolution_provider_attempts (lead_id, started_at);

CREATE INDEX IF NOT EXISTS entity_resolution_provider_attempts_failure_idx
    ON growth.entity_resolution_provider_attempts (provider, status, error_code)
    WHERE status <> 'SUCCEEDED';
