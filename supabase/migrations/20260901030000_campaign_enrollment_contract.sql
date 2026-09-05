-- Align campaign enrollment storage with the shared campaign-enrollment contract.
-- Applied migrations remain immutable. Re-runnable on persistent integration databases.

alter table public.campaign_enrollments
  add column if not exists account_id text,
  add column if not exists priority_at_enrollment text;

update public.campaign_enrollments
set account_id = coalesce(account_id, metadata->>'account_id', 'unknown')
where account_id is null;

update public.campaign_enrollments
set priority_at_enrollment = coalesce(
  priority_at_enrollment,
  metadata->>'priority_at_enrollment',
  'P3'
)
where priority_at_enrollment is null;

alter table public.campaign_enrollments
  alter column account_id set not null,
  alter column priority_at_enrollment set not null;

do $ci$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'campaign_enrollments_priority_chk'
      and conrelid = 'public.campaign_enrollments'::regclass
  ) then
    alter table public.campaign_enrollments
      add constraint campaign_enrollments_priority_chk
      check (priority_at_enrollment in ('P1','P2','P3','P4'));
  end if;
end
$ci$;

create index if not exists campaign_enrollments_account_idx
  on public.campaign_enrollments(account_id, enrolled_at desc);
