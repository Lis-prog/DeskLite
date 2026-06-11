# Contributing to DeskLite

This is our shared workflow. It keeps five people building in parallel without conflicts.
For *what* to build and the design/security rules, read **`AGENTS.md`** first.

## 1. One-time setup
1. Install Docker Desktop (see `DeskLite_Team_Setup_Guide.docx`), Git, and VS Code.
2. `git clone <repo-url> && cd desklite`
3. `cp .env.example .env`   (Windows: `copy .env.example .env`)
4. `docker compose up --build`
5. Open: app http://localhost:3000 · API docs http://localhost:8000/docs · MinIO http://localhost:9001

## 2. Daily loop
```bash
git checkout main
git pull origin main                 # always start from latest
git checkout -b feature/<area>-<short>
# ... do the work for ONE ticket ...
git add .
git commit -m "feat: short description (DESK-123)"
git push -u origin feature/<area>-<short>
gh pr create                         # open a PR, fill the template
```
Then: a teammate reviews → CI goes green → **squash & merge** → delete the branch.

## 3. Rules of the road
- **Small PRs.** One ticket per PR. Easier to review, fewer conflicts.
- **Never push to `main`.** It's protected; everything goes through a PR.
- **Conventional Commits**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- **Update `.env.example`** in the same PR whenever you read a new env var in code.
- **Migrations**: only one Alembic migration merges at a time; coordinate with Paulina. Run
  `alembic upgrade head` after pulling new migrations.
- **API contract first**: agree request/response shape in the ticket/PR before the frontend builds on it.
- **Rebuild when needed**: `docker compose up --build` after dependency or Dockerfile changes.

## 4. Before you open a PR — checklist
- [ ] Acceptance criteria met
- [ ] Tests added/updated, passing locally (`pytest` / `npm test`)
- [ ] Lint/type-check clean (`ruff check .` / `npm run lint` / `tsc --noEmit`)
- [ ] No secrets committed; `.env.example` updated if needed
- [ ] PR description links the `DESK-` ticket and explains how to test

## 5. Handy commands
```bash
docker compose up --build      # start everything
docker compose logs -f backend # tail a service
docker compose down            # stop (keeps data)
docker compose down -v         # stop + WIPE the database volume
gh pr checks                   # see CI status on your PR
```
