-- Harden the Phase 1 immutable trigger function against search_path manipulation.

CREATE OR REPLACE FUNCTION growth.prevent_phase1_immutable_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, growth
AS $$
BEGIN
    RAISE EXCEPTION 'phase1 immutable table % cannot be mutated', TG_TABLE_NAME;
END;
$$;
