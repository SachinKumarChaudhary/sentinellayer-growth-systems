create or replace function crm.prevent_append_only_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $$
begin
  raise exception 'CRM append-only record cannot be updated or deleted';
end;
$$;
