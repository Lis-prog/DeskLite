<!-- Keep PRs small and focused on ONE ticket. See CONTRIBUTING.md. -->

## What & why
<!-- What does this change do, and why? Link the ticket. -->
Closes DESK-

## How to test
<!-- Steps a reviewer can follow to verify it works. -->
1.

## Checklist
- [ ] Acceptance criteria met
- [ ] Tests added/updated and passing locally
- [ ] Lint & type-check clean (`ruff check .` / `npm run lint` + `npm run typecheck`)
- [ ] No secrets committed; `.env.example` updated if I added a config var
- [ ] Follows the golden rules in `permission-matrix.md` (identity from token, field whitelist, RBAC + ownership)
- [ ] Database change? Includes an Alembic migration and Paulina is aware
