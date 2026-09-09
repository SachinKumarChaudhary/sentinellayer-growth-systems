-- Keep evidence persistence compatible with the repository's ON CONFLICT (evidence_hash) contract.
CREATE UNIQUE INDEX IF NOT EXISTS evidence_hash_all_uidx
  ON intelligence.evidence (evidence_hash);
