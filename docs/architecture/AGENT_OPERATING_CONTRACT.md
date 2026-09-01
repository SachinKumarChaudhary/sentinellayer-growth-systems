# Agent Operating Contract

## Required reading order
1. `docs/architecture/SYSTEM_MAP.md`
2. `docs/architecture/OWNERSHIP.md`
3. `docs/architecture/DEPENDENCIES.md`
4. owning system specification
5. `docs/platform/CONTRACTS.md`
6. relevant schemas and tests

## Before changing code
Identify owner; inspect current state; identify dependencies/consumers; determine whether the change crosses a contract; inspect migrations; never overwrite stale versions; never rewrite applied migrations.

## Definition of Done
As applicable: implementation, contract/schema update, migration, RLS/security validation, unit tests, contract tests, integration tests, real Supabase validation, documentation, green CI, and explicit handoff.

## Forbidden
Do not silently change another system's contract, duplicate domain logic, bypass RLS for convenience, commit secrets, mutate another domain's tables without a contract, claim production readiness without required tests, or claim a tool operation succeeded without verification.

## Shared-contract protocol
Proposal → producer/consumer identification → compatibility decision → schema/version update → implementation → integration test → full CI.

## Handoff artifact
Record what changed, files changed, contract/version changes, DB/RLS changes, tests run, known limitations, and receiving agent's next action.
