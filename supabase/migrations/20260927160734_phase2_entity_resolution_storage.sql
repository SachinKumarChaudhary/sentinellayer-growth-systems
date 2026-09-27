-- Phase 2 durable entity-resolution storage.
-- Immutable adjudication/evidence records are separated from mutable run state.

CREATE SCHEMA IF NOT EXISTS growth;

CREATE TABLE IF NOT EXISTS growth.entity_resolution_runs (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_key text NOT NULL UNIQUE,
    contract_version text NOT NULL,
    matching_version text NOT NULL,
    status text NOT NULL DEFAULT 'RUNNING',
    started_at timestamptz NOT NULL,
    completed_at timestamptz,
    input_count integer NOT NULL DEFAULT 0,
    decision_count integer NOT NULL DEFAULT 0,
    candidate_count integer NOT NULL DEFAULT 0,
    escalation_count integer NOT NULL DEFAULT 0,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (status IN ('RUNNING','COMPLETED','FAILED','CANCELLED')),
    CHECK (input_count >= 0),
    CHECK (decision_count >= 0),
    CHECK (candidate_count >= 0),
    CHECK (escalation_count >= 0),
    CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE INDEX IF NOT EXISTS entity_resolution_runs_status_idx
    ON growth.entity_resolution_runs (status, started_at);

CREATE TABLE IF NOT EXISTS growth.entity_resolution_candidates (
    run_id uuid NOT NULL
        REFERENCES growth.entity_resolution_runs(run_id) ON DELETE RESTRICT,
    candidate_id text NOT NULL,
    lead_id text NOT NULL,
    entity_id text,
    entity_type text NOT NULL,
    canonical_name text NOT NULL,
    canonical_domain text,
    aliases jsonb NOT NULL DEFAULT '[]'::jsonb,
    geography jsonb NOT NULL DEFAULT '[]'::jsonb,
    legal_identifier text,
    official_url text,
    domain_verified boolean NOT NULL DEFAULT false,
    official_corporate_url_match boolean NOT NULL DEFAULT false,
    explicit_official_identity_tie boolean NOT NULL DEFAULT false,
    registered_identity_match boolean NOT NULL DEFAULT false,
    corporate_social_match boolean NOT NULL DEFAULT false,
    parent_relationship_consistent boolean NOT NULL DEFAULT false,
    historical_only boolean NOT NULL DEFAULT false,
    clearly_different_legal_entity boolean NOT NULL DEFAULT false,
    conflicting_authoritative_domain boolean NOT NULL DEFAULT false,
    conflicting_geography boolean NOT NULL DEFAULT false,
    external_provider_relationship boolean NOT NULL DEFAULT false,
    currentness text NOT NULL,
    evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    origin text NOT NULL,
    candidate_payload jsonb NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, candidate_id),
    CHECK (jsonb_typeof(aliases) = 'array'),
    CHECK (jsonb_typeof(geography) = 'array'),
    CHECK (jsonb_typeof(evidence_refs) = 'array'),
    CHECK (jsonb_typeof(candidate_payload) = 'object'),
    CHECK (entity_type IN (
        'LEGAL_ENTITY','OPERATING_ENTITY','BRAND','BUSINESS_UNIT',
        'PARENT_COMPANY','HOLDING_COMPANY','FRANCHISEE','LICENSOR',
        'LICENSEE','EXTERNAL_PROVIDER','UNKNOWN'
    )),
    CHECK (currentness IN ('CURRENT','HISTORICAL','UNKNOWN','NOT_ESTABLISHED','CONFLICT')),
    CHECK (origin IN ('phase1','provider','research','gold'))
);

CREATE INDEX IF NOT EXISTS entity_resolution_candidates_lead_idx
    ON growth.entity_resolution_candidates (lead_id, run_id);

CREATE INDEX IF NOT EXISTS entity_resolution_candidates_entity_idx
    ON growth.entity_resolution_candidates (entity_id, run_id);

CREATE TABLE IF NOT EXISTS growth.entity_resolution_comparisons (
    run_id uuid NOT NULL,
    candidate_id text NOT NULL,
    lead_id text NOT NULL,
    score integer NOT NULL,
    signals jsonb NOT NULL DEFAULT '[]'::jsonb,
    hard_negative boolean NOT NULL DEFAULT false,
    eligible_for_match boolean NOT NULL DEFAULT false,
    comparison_payload jsonb NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, candidate_id),
    FOREIGN KEY (run_id, candidate_id)
        REFERENCES growth.entity_resolution_candidates(run_id, candidate_id)
        ON DELETE RESTRICT,
    CHECK (jsonb_typeof(signals) = 'array'),
    CHECK (jsonb_typeof(comparison_payload) = 'object')
);

CREATE INDEX IF NOT EXISTS entity_resolution_comparisons_lead_idx
    ON growth.entity_resolution_comparisons (lead_id, run_id);

CREATE TABLE IF NOT EXISTS growth.entity_resolution_relationships (
    run_id uuid NOT NULL,
    relationship_id text NOT NULL,
    lead_id text NOT NULL,
    subject_entity_id text NOT NULL,
    predicate text NOT NULL,
    object_entity_id text NOT NULL,
    function_scope text,
    valid_from timestamptz,
    valid_to timestamptz,
    currentness text NOT NULL,
    evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    status text NOT NULL,
    adjudication_reason text NOT NULL,
    relationship_payload jsonb NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, relationship_id),
    CHECK (jsonb_typeof(evidence_refs) = 'array'),
    CHECK (jsonb_typeof(relationship_payload) = 'object'),
    CHECK (currentness IN ('CURRENT','HISTORICAL','UNKNOWN','NOT_ESTABLISHED','CONFLICT')),
    CHECK (status IN ('ESTABLISHED','NOT_ESTABLISHED','CONFLICT','UNKNOWN')),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_from <= valid_to)
);

CREATE INDEX IF NOT EXISTS entity_resolution_relationships_subject_idx
    ON growth.entity_resolution_relationships (subject_entity_id, currentness);

CREATE INDEX IF NOT EXISTS entity_resolution_relationships_object_idx
    ON growth.entity_resolution_relationships (object_entity_id, currentness);

CREATE TABLE IF NOT EXISTS growth.entity_resolution_decisions (
    run_id uuid NOT NULL
        REFERENCES growth.entity_resolution_runs(run_id) ON DELETE RESTRICT,
    decision_id text NOT NULL,
    lead_id text NOT NULL,
    contract_version text NOT NULL,
    status text NOT NULL,
    canonical_entity_id text,
    entity_type text NOT NULL,
    canonical_name text,
    canonical_domain text,
    confidence text NOT NULL,
    decisive_signals jsonb NOT NULL DEFAULT '[]'::jsonb,
    rejected_candidates jsonb NOT NULL DEFAULT '[]'::jsonb,
    evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    currentness text NOT NULL,
    research_required boolean NOT NULL DEFAULT false,
    research_missions jsonb NOT NULL DEFAULT '[]'::jsonb,
    unresolved_questions jsonb NOT NULL DEFAULT '[]'::jsonb,
    matching_version text NOT NULL,
    decided_at timestamptz NOT NULL,
    decision_payload jsonb NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, decision_id),
    UNIQUE (run_id, lead_id),
    CHECK (status IN (
        'MATCHED','MATCHED_WITH_RELATIONSHIP','AMBIGUOUS',
        'CONFLICT','UNRESOLVED','NO_MATCH'
    )),
    CHECK (entity_type IN (
        'LEGAL_ENTITY','OPERATING_ENTITY','BRAND','BUSINESS_UNIT',
        'PARENT_COMPANY','HOLDING_COMPANY','FRANCHISEE','LICENSOR',
        'LICENSEE','EXTERNAL_PROVIDER','UNKNOWN'
    )),
    CHECK (confidence IN ('high','medium','low','unknown')),
    CHECK (currentness IN ('CURRENT','HISTORICAL','UNKNOWN','NOT_ESTABLISHED','CONFLICT')),
    CHECK (jsonb_typeof(decisive_signals) = 'array'),
    CHECK (jsonb_typeof(rejected_candidates) = 'array'),
    CHECK (jsonb_typeof(evidence_refs) = 'array'),
    CHECK (jsonb_typeof(research_missions) = 'array'),
    CHECK (jsonb_typeof(unresolved_questions) = 'array'),
    CHECK (jsonb_typeof(decision_payload) = 'object'),
    CHECK (
        (status IN ('MATCHED','MATCHED_WITH_RELATIONSHIP') AND canonical_entity_id IS NOT NULL)
        OR status IN ('AMBIGUOUS','CONFLICT','UNRESOLVED','NO_MATCH')
    ),
    CHECK (
        (status IN ('MATCHED','MATCHED_WITH_RELATIONSHIP') AND jsonb_array_length(evidence_refs) > 0)
        OR status IN ('AMBIGUOUS','CONFLICT','UNRESOLVED','NO_MATCH')
    )
);

CREATE INDEX IF NOT EXISTS entity_resolution_decisions_lead_idx
    ON growth.entity_resolution_decisions (lead_id, decided_at DESC);

CREATE INDEX IF NOT EXISTS entity_resolution_decisions_entity_idx
    ON growth.entity_resolution_decisions (canonical_entity_id, currentness);

CREATE TABLE IF NOT EXISTS growth.entity_resolution_decision_traces (
    run_id uuid NOT NULL,
    decision_id text NOT NULL,
    trace_no integer NOT NULL,
    step text NOT NULL,
    detail text NOT NULL,
    candidate_id text,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, decision_id, trace_no),
    FOREIGN KEY (run_id, decision_id)
        REFERENCES growth.entity_resolution_decisions(run_id, decision_id)
        ON DELETE RESTRICT,
    CHECK (trace_no >= 0)
);

CREATE TABLE IF NOT EXISTS growth.entity_resolution_provider_attempts (
    attempt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL
        REFERENCES growth.entity_resolution_runs(run_id) ON DELETE RESTRICT,
    mission_id text,
    provider text NOT NULL,
    operation text NOT NULL,
    request_fingerprint char(64),
    request_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL,
    provider_request_id text,
    result_count integer,
    latency_ms integer,
    cost_units numeric,
    error_code text,
    error_message text,
    started_at timestamptz NOT NULL,
    completed_at timestamptz,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    CHECK (request_fingerprint IS NULL OR request_fingerprint ~ '^[0-9a-f]{64}$'),
    CHECK (jsonb_typeof(request_payload) = 'object'),
    CHECK (jsonb_typeof(metadata) = 'object'),
    CHECK (status IN ('STARTED','SUCCEEDED','FAILED','RATE_LIMITED','CACHED'))
);

CREATE INDEX IF NOT EXISTS entity_resolution_provider_attempts_run_idx
    ON growth.entity_resolution_provider_attempts (run_id, started_at);

CREATE INDEX IF NOT EXISTS entity_resolution_provider_attempts_request_idx
    ON growth.entity_resolution_provider_attempts (request_fingerprint);

CREATE TABLE IF NOT EXISTS growth.entity_resolution_research_observations (
    run_id uuid NOT NULL
        REFERENCES growth.entity_resolution_runs(run_id) ON DELETE RESTRICT,
    observation_id text NOT NULL,
    mission_id text NOT NULL,
    provider text NOT NULL,
    observation_type text NOT NULL,
    result_position integer,
    url text,
    final_url text,
    source_domain text,
    title text,
    snippet text,
    text_content text,
    published_at timestamptz,
    observed_at timestamptz NOT NULL,
    request_params jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    search_linked boolean NOT NULL DEFAULT false,
    observation_payload jsonb NOT NULL,
    PRIMARY KEY (run_id, observation_id),
    CHECK (observation_type IN ('SEARCH_RESULT','FETCH_RESULT')),
    CHECK (result_position IS NULL OR result_position >= 0),
    CHECK (jsonb_typeof(request_params) = 'object'),
    CHECK (jsonb_typeof(provenance) = 'object'),
    CHECK (jsonb_typeof(observation_payload) = 'object')
);

CREATE INDEX IF NOT EXISTS entity_resolution_research_observations_mission_idx
    ON growth.entity_resolution_research_observations (run_id, mission_id, observed_at);

CREATE INDEX IF NOT EXISTS entity_resolution_research_observations_url_idx
    ON growth.entity_resolution_research_observations (url);

CREATE TABLE IF NOT EXISTS growth.entity_resolution_evaluation_results (
    evaluation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL
        REFERENCES growth.entity_resolution_runs(run_id) ON DELETE RESTRICT,
    benchmark_version text NOT NULL,
    case_id text NOT NULL,
    entity_type_score numeric(5,4),
    ownership_score numeric(5,4),
    operating_entity_score numeric(5,4),
    relationship_score numeric(5,4),
    functional_control_score numeric(5,4),
    currentness_score numeric(5,4),
    evidence_quality_score numeric(5,4),
    false_positive_safety_score numeric(5,4),
    total_score numeric(6,4),
    critical_failure boolean NOT NULL DEFAULT false,
    passed boolean NOT NULL,
    expected_payload jsonb NOT NULL,
    observed_payload jsonb NOT NULL,
    evaluator_version text NOT NULL,
    evaluated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, benchmark_version, case_id),
    CHECK (entity_type_score IS NULL OR entity_type_score BETWEEN 0 AND 1),
    CHECK (ownership_score IS NULL OR ownership_score BETWEEN 0 AND 1),
    CHECK (operating_entity_score IS NULL OR operating_entity_score BETWEEN 0 AND 1),
    CHECK (relationship_score IS NULL OR relationship_score BETWEEN 0 AND 1),
    CHECK (functional_control_score IS NULL OR functional_control_score BETWEEN 0 AND 1),
    CHECK (currentness_score IS NULL OR currentness_score BETWEEN 0 AND 1),
    CHECK (evidence_quality_score IS NULL OR evidence_quality_score BETWEEN 0 AND 1),
    CHECK (false_positive_safety_score IS NULL OR false_positive_safety_score BETWEEN 0 AND 1),
    CHECK (expected_payload IS NOT NULL AND jsonb_typeof(expected_payload) = 'object'),
    CHECK (observed_payload IS NOT NULL AND jsonb_typeof(observed_payload) = 'object')
);

CREATE INDEX IF NOT EXISTS entity_resolution_evaluation_results_run_idx
    ON growth.entity_resolution_evaluation_results (run_id, benchmark_version, evaluated_at);

-- Immutable Phase 2 evidence and adjudication records are never updated or deleted.
CREATE OR REPLACE FUNCTION growth.prevent_phase2_immutable_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'phase2 immutable table % cannot be mutated', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS entity_resolution_candidates_immutable
    ON growth.entity_resolution_candidates;
CREATE TRIGGER entity_resolution_candidates_immutable
    BEFORE UPDATE OR DELETE ON growth.entity_resolution_candidates
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase2_immutable_mutation();

DROP TRIGGER IF EXISTS entity_resolution_comparisons_immutable
    ON growth.entity_resolution_comparisons;
CREATE TRIGGER entity_resolution_comparisons_immutable
    BEFORE UPDATE OR DELETE ON growth.entity_resolution_comparisons
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase2_immutable_mutation();

DROP TRIGGER IF EXISTS entity_resolution_relationships_immutable
    ON growth.entity_resolution_relationships;
CREATE TRIGGER entity_resolution_relationships_immutable
    BEFORE UPDATE OR DELETE ON growth.entity_resolution_relationships
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase2_immutable_mutation();

DROP TRIGGER IF EXISTS entity_resolution_decisions_immutable
    ON growth.entity_resolution_decisions;
CREATE TRIGGER entity_resolution_decisions_immutable
    BEFORE UPDATE OR DELETE ON growth.entity_resolution_decisions
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase2_immutable_mutation();

DROP TRIGGER IF EXISTS entity_resolution_decision_traces_immutable
    ON growth.entity_resolution_decision_traces;
CREATE TRIGGER entity_resolution_decision_traces_immutable
    BEFORE UPDATE OR DELETE ON growth.entity_resolution_decision_traces
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase2_immutable_mutation();

DROP TRIGGER IF EXISTS entity_resolution_provider_attempts_immutable
    ON growth.entity_resolution_provider_attempts;
CREATE TRIGGER entity_resolution_provider_attempts_immutable
    BEFORE UPDATE OR DELETE ON growth.entity_resolution_provider_attempts
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase2_immutable_mutation();

DROP TRIGGER IF EXISTS entity_resolution_research_observations_immutable
    ON growth.entity_resolution_research_observations;
CREATE TRIGGER entity_resolution_research_observations_immutable
    BEFORE UPDATE OR DELETE ON growth.entity_resolution_research_observations
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase2_immutable_mutation();

DROP TRIGGER IF EXISTS entity_resolution_evaluation_results_immutable
    ON growth.entity_resolution_evaluation_results;
CREATE TRIGGER entity_resolution_evaluation_results_immutable
    BEFORE UPDATE OR DELETE ON growth.entity_resolution_evaluation_results
    FOR EACH ROW EXECUTE FUNCTION growth.prevent_phase2_immutable_mutation();

ALTER TABLE growth.entity_resolution_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.entity_resolution_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.entity_resolution_comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.entity_resolution_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.entity_resolution_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.entity_resolution_decision_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.entity_resolution_provider_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.entity_resolution_research_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE growth.entity_resolution_evaluation_results ENABLE ROW LEVEL SECURITY;
