-- Keep enrichment persistence timestamps aligned with the canonical repository contract.
ALTER TABLE growth.company_contacts
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE growth.decision_maker_contact_methods
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
