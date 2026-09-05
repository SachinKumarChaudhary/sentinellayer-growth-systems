-- Operations control-plane state
CREATE SCHEMA IF NOT EXISTS operations;

CREATE TABLE IF NOT EXISTS operations.control_state (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  environment text NOT NULL CHECK (environment IN ('development','staging','production')),
  outbound_state text NOT NULL CHECK (outbound_state IN ('DISABLED','ARMED','ENABLED','SAFE_STOP')),
  maintenance_mode boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NOT NULL
);

CREATE TABLE IF NOT EXISTS operations.control_audit (
  audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  changed_at timestamptz NOT NULL DEFAULT now(),
  changed_by text NOT NULL,
  action text NOT NULL,
  previous_state jsonb,
  new_state jsonb NOT NULL,
  reason text
);

ALTER TABLE operations.control_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE operations.control_audit ENABLE ROW LEVEL SECURITY;

-- Fail closed by default: initialize a single DISABLED row for each deployment
-- only when no state exists. The service role/admin boundary owns mutations.
INSERT INTO operations.control_state (
  environment, outbound_state, maintenance_mode, updated_by
)
VALUES ('development', 'DISABLED', true, 'migration')
ON CONFLICT (singleton) DO NOTHING;
