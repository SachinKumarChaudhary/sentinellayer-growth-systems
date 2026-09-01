# Migration Rules

Domain migrations are owned by their domain. Platform owns shared database primitives and cross-system conventions.

1. Applied migrations are immutable.
2. Never rewrite production history.
3. Use uniquely timestamped migration filenames.
4. Prefer additive changes.
5. Breaking changes require compatibility planning.
6. Cross-domain foreign keys require an explicit contract.
7. RLS is required for every exposed domain table according to its owner.
8. Minimize and justify service-role operations.
9. Test important constraints against real Supabase where practical.
10. Never put secrets in migrations.

Safe sequence: Design → migration → RLS → contract update if needed → validation → real Supabase validation → CI → deployment.
