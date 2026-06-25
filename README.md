# DeskLite

An internal support-ticket system. Customers raise tickets, agents work them through their
lifecycle, and managers track everything on a live dashboard — with strict role-based access control.

**Stack:** Next.js + React + TypeScript + Tailwind · FastAPI + Python 3.12 · PostgreSQL · MinIO (S3) · Docker · GitHub Actions

> New to the project? Read **`.github/docs/architecture/permission-matrix.md`** (roles & security rules) and **`CONTRIBUTING.md`** (how we collaborate).  
> **Production deploy:** see **`DEPLOY.md`** (Contabo VPS + HTTPS).

## Run it locally (one command)

1. Install **Docker Desktop** and start it (wait for "Engine running"). See `DeskLite_Team_Setup_Guide.docx`.
2. Copy the env template:
   ```bash
   cp .env.example .env      # Windows: copy .env.example .env
   ```
3. Bring up the whole stack:
   ```bash
   docker compose up --build
   ```
4. Open:
   - App (frontend): http://localhost:3000
   - API docs (Swagger): http://localhost:8000/docs
   - API health check: http://localhost:8000/api/v1/health
   - MinIO console: http://localhost:9001

To stop: `docker compose down` (add `-v` to also wipe the database).

## Project layout

```
backend/    FastAPI app (API, models, schemas, migrations, tests)
frontend/   Next.js app (pages, components, design system)
.github/    CI pipeline, PR template, and architecture docs
```

## Common commands

```bash
docker compose up --build        # start everything (rebuild images)
docker compose logs -f backend   # tail one service
docker compose down              # stop
docker compose down -v           # stop + wipe DB volume
docker compose exec backend python seed.py   # load demo users and tickets
```

After seeding, sign in with any printed account (e.g. `admin@desklite.dev` / `Admin1234!`).

## Team

| Person | Role |
|---|---|
| Egzona Haskuka | Frontend Lead |
| Valza Dalipi | Tech Lead |
| Paulina Delija | Backend / Data |
| Rrezart Buzuku | Full-Stack Integration |
| Lis Pruthi | DevOps & QA |

## Demo data (presentation)

Load realistic users and tickets after the stack is up:

```bash
docker compose exec backend python seed.py
```

Example logins (after seed — see script output for current passwords if customized):

| Role | Email | Use for |
|------|-------|---------|
| Admin | admin@desklite.local | Dashboard, assign tickets |
| Agent | agent@desklite.local | Queue, status transitions |
| Customer | customer@desklite.local | Create/view own tickets |

## Run tests

```bash
# Backend (inside container)
docker compose exec backend pytest
docker compose exec backend ruff check .

# Frontend
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run build
```

## End-to-end tests (Playwright)

Requires the stack running at http://localhost:3000.

```bash
cd e2e
npm ci
npx playwright install chromium
npm test
```

Set `BASE_URL=http://localhost:3000` if the app runs elsewhere.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker compose` fails on Windows | Start Docker Desktop; wait for "Engine running" |
| Port 3000/8000 in use | Stop other apps or change ports in `docker-compose.yml` |
| Backend unhealthy | `docker compose logs -f backend` then `docker compose exec backend alembic upgrade head` |
| Login fails locally | Copy `.env.example` → `.env`; use `COOKIE_SECURE=false` for http://localhost |
| CI fails on coverage | Add tests under `backend/tests/`; floor is 80% (`cov-fail-under=80`) |
| Staging deploy fails | Set GitHub secrets `STAGING_VPS_*` (see `DEPLOY.md`) |
| Uptime workflow skips | Set repo variable `HEALTHCHECK_URL` to your API base URL |

## GitHub repo variables (optional)

| Variable | Purpose |
|----------|---------|
| `STAGING_URL` | Link shown on staging deploy workflow |
| `HEALTHCHECK_URL` | Enables scheduled uptime probes in `.github/workflows/uptime.yml` |

