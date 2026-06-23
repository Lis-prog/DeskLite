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
