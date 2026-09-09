-- Keep enrichment persistence aligned with the repository contract.
ALTER TABLE growth.company_contacts
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE growth.decision_maker_contact_methods
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS company_contacts_company_channel_value_uidx
  ON growth.company_contacts (company_id, channel, normalized_value);

CREATE UNIQUE INDEX IF NOT EXISTS decision_maker_contact_methods_dm_channel_value_uidx
  ON growth.decision_maker_contact_methods (decision_maker_id, channel, normalized_value);

CREATE UNIQUE INDEX IF NOT EXISTS decision_makers_company_name_title_uidx
  ON growth.decision_makers (company_id, lower(full_name), lower(coalesce(title, '')));
