-- Phase 1 durable lead-intake storage.
-- Raw source observations and adjudication records are append-only.
-- Mutable processing state and canonical projection are separate from raw evidence.

CREATE SCHEMA IF NOT EXISTS growth;

CREATE TABLE IF NOT EXISTS growth.lead_source_records (
    source_record_id text PRIMARY KEY,
    schema_version text NOT NULL,
    source_name text NOT NULL,
    source_version text,
    source_record_key text,
    acquired_at timestamptz NOT NULL,
    source_payload jsonb NOT NULL,
    mapped_fields jsonb NOT NULL DEFAULT '[]'::jsonb,
    raw_fingerprint char(64) NOT NULL,
    adapter_version text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(source_payload) = 'object'),
    CHECK (jsonb_typeof(mapped_fields) = 'array'),
    CHECK (raw_fingerprint ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS lead_source_records_source_fingerprint_idx
    ON growth.lead_source_records (source_name, raw_fingerprint);

CREATE TABLE IF NOT EXISTS growth.lead_processing_state (
    source_record_id text PRIMARY KEY
        REFERENCES growth.lead_source_records(source_record_id) ON DELETE RESTRICT,
    state text NOT NULL,
    lead_id text,
    quality_status text,
    contract_version text NOT NULL,
    validation_version text,
    normalization_version text,
    processed_at timestamptz,
    last_error text,
    retry_count integer NOT NULL DEFAULT 0,
    next_retry_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (state IN (
        'RECEIVED','NORMALIZED','VALIDATED','ACCEPTED',
        'ACCEPTED_WITH_WARNINGS','QUARANTINED','REJECTED','DUPLICATE'
    )),
    CHECK (quality_status IS NULL OR quality_status IN (
        'ACCEPTED','ACCEPTED_WITH_WARNINGS','QUARANTINED','REJECTED','DUPLICATE'
    )),
    CHECK (retry_count >= 0)
);

CREATE INDEX IF NOT EXISTS lead_processing_state_retry_idx
    ON growth.lead_processing_state (state, next_retry_at);

CREATE TABLE IF NOT EXISTS growth.lead_field_observations (
    observation_id text PRIMARY KEY,
    lead_id text NOT NULL,
    source_record_id text NOT NULL
        REFERENCES growth.lead_source_records(source_record_id) ON DELETE RESTRICT,
    field text NOT NULL,
    source_field_name text NOT NULL,
    raw_value jsonb,
    normalized_value jsonb,
    value_state text NOT NULL,
    observed_at timestamptz NOT NULL,
    adapter_version text NOT NULL,
    normalization_version text NOT NULL,
    transformation_reason text NOT NULL,
    CHECK (value_state IN ('observed','normalized','missing','invalid','conflicting'))
);

CREATE INDEX IF NOT EXISTS lead_field_observations_lead_idx
    ON growth.lead_field_observations (lead_id, observed_at);

CREATE INDEX IF NOT EXISTS lead_field_observations_source_idx
    ON growth.lead_field_observations (source_record_id);

CREATE TABLE IF NOT EXISTS growth.lead_validation_findings (
    finding_id text PRIMARY KEY,
    source_record_id text
        REFERENCES growth.lead_source_records(source_record_id) ON DELETE RESTRICT,
    lead_id text,
    field text,
    rule_id text NOT NULL,
    severity text NOT NULL,
    code text NOT NULL,
    message text NOT NULL,
    observed_value_ref text,
    created_at timestamptz NOT NULL,
    validation_version text NOT NULL,
    CHECK (severity IN ('ERROR','WARNING','INFO'))
);

CREATE INDEX IF NOT EXISTS lead_validation_findings_source_idx
    ON growth.lead_validation_findings (source_record_id, severity);

CREATE TABLE IF NOT EXISTS growth.lead_duplicate_decisions (
    decision_id text PRIMARY KEY,
    source_record_id text NOT NULL
        REFERENCES growth.lead_source_records(source_record_id) ON DELETE RESTRICT,
    duplicate_type text NOT NULL,
    rule_id text NOT NULL,
    matched_source_record_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    comparison_keys jsonb NOT NULL DEFAULT '{}'::jsonb,
    decided_at timestamptz NOT NULL,
    decision_version text NOT NULL,
    CHECK (duplicate_type IN ('replay','exact_duplicate','not_duplicate')),
    CHECK (jsonb_typeof(matched_source_record_ids) = 'array'),
    CHECK (jsonb_typeof(comparison_keys) = 'object')
);

CREATE INDEX IF NOT EXISTS lead_duplicate_decisions_source_idx
    ON growth.lead_duplicate_decisions (source_record_id, decided_at);

CREATE TABLE IF NOT EXISTS growth.lead_canonical_projection (
    lead_id text PRIMARY KEY,
    display_name text,
    legal_name text,
    domain text,
    canonical_url text,
    country_code text,
    region text,
    city text,
    postal_code text,
    platform text,
    source_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    normalization_version text NOT NULL,
    raw_fingerprint char(64) NOT NULL,
    source_fingerprint char(64) NOT NULL,
    canonical_fingerprint char(64) NOT NULL,
    quality_status text NOT NULL,
    quality_finding_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CHECK (jsonb_typeof(source_refs) = 'array'),
    CHECK (jsonb_typeof(quality_finding_ids) = 'array'),
    CHECK (raw_fingerprint ~ '^[0-9a-f]{64}$'),
    CHECK (source_fingerprint ~ '^[0-9a-f]{64}$'),
    CHECK (canonical_fingerprint ~ '^[0-9a-f]{64}$'),
    CHECK (quality_status IN (
        'ACCEPTED','ACCEPTED_WITH_WARNINGS','QUARANTINED','REJECTED','DUPLICATE'
    ))
);

CREATE INDEX IF NOT EXISTS lead_canonical_projection_fingerprint_idx
    ON growth.lead_canonical_projection (canonical_fingerprint);

CREATE TABLE IF NOT EXISTS growth.lead_quarantine (
    source_record_id text PRIMARY KEY
        REFERENCES growth.lead_source_records(source_record_id) ON DELETE RESTRICT,
    lead_id text,
    finding_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    retry_count integer NOT NULL DEFAULT 0,
    next_retry_at timestamptz,
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(finding_ids) = 'array'),
    CHECK (retry_count >= 0)
);

CREATE TABLE IF NOT EXISTS growth.lead_phase1_handoffs (
    handoff_id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    lead_id text NOT NULL,
    canonical_fingerprint char(64) NOT NULL,
    contract_version text NOT NULL,
    quality_status text NOT NULL,
    downstream_eligible boolean NOT NULL,
    handoff_payload jsonb NOT NULL,
    completed_at timestamptz NOT NULL,
    UNIQUE (lead_id, canonical_fingerprint),
    CHECK (canonical_fingerprint ~ '^[0-9a-f]{64}$'),
    CHECK (quality_status IN (
        'ACCEPTED','ACCEPTED_WITH_WARNINGS','QUARANTINED','REJECTED','DUPLICATE'
    )),
    CHECK (jsonb_typeof(handoff_payload) = 'object')
);

CREATE INDEX IF NOT EXISTS lead_phase1_handoffs_eligibility_idx
    ON growth.lead_phase1_handoffs (downstream_eligible, completed_at);

-- Raw observations and adjudication records must not be mutable.
CREATE OR REPLACE FUNCTION growth.prevent_phase1_immutable_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'phase1 immutable table % cannot be mutated', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS lead_source_records_immutable ON growth.lead_source_records;
CREATE TRIGGER lead_source_records_immutable
    BEFORE UPDATE OR DELETE ON growth.lead_source_records
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase1_immutable_mutation();

DROP TRIGGER IF EXISTS lead_field_observations_immutable ON growth.lead_field_observations;
CREATE TRIGGER lead_field_observations_immutable
    BEFORE UPDATE OR DELETE ON growth.lead_field_observations
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase1_immutable_mutation();

DROP TRIGGER IF EXISTS lead_validation_findings_immutable ON growth.lead_validation_findings;
CREATE TRIGGER lead_validation_findings_immutable
    BEFORE UPDATE OR DELETE ON growth.lead_validation_findings
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase1_immutable_mutation();

DROP TRIGGER IF EXISTS lead_duplicate_decisions_immutable ON growth.lead_duplicate_decisions;
CREATE TRIGGER lead_duplicate_decisions_immutable
    BEFORE UPDATE OR DELETE ON growth.lead_duplicate_decisions
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase1_immutable_mutation();

ALTER TABLE growth.lead_source_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.lead_processing_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.lead_field_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.lead_validation_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.lead_duplicate_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.lead_canonical_projection ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.lead_quarantine ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.lead_phase1_handoffs ENABLE ROW LEVEL SECURITY;
