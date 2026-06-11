# DeskLite — Team Blueprint & Working Agreement

> **Read this before writing a single line of code.** This is the single source of truth for *how*
> we build DeskLite. If you (or your AI agent in Cursor) follow this document, our five parts will
> fit together cleanly and we avoid the "you changed this, I changed that" chaos.
>
> **Rule of thumb:** if something here is unclear or you want to change a convention, you do **not**
> silently do it your own way — you raise it with the team (Valza, Tech Lead) and we update this file
> *first*. The blueprint changes by agreement, never by surprise.

---

## 1. What we are building

**DeskLite** is an internal support-ticket system. Three roles:

| Role | Can do |
|---|---|
| **Customer** | Create tickets, see **only their own** tickets, comment on them |
| **Agent** | See tickets **assigned to them**, update status, comment |
| **Admin / Manager** | See **all** tickets, assign agents, view the dashboard |

The product is "done" when a user can register, log in, create a ticket, an agent works it through
its lifecycle, files/comments are attached, and a manager sees live metrics — all with each role
strictly limited to what it's allowed to do.

---

## 2. The stack (do not substitute without team agreement)

| Layer | Technology | Notes |
|---|---|---|
| Frontend | **Next.js (App Router) + React + TypeScript + Tailwind CSS** | `frontend/` |
| Backend | **FastAPI + Python 3.12 + Pydantic v2** | `backend/` |
| ORM / Migrations | **SQLAlchemy 2.x + Alembic** | |
| Database | **PostgreSQL 16** | runs in Docker |
| Object storage | **MinIO** (S3-compatible) | runs in Docker; for attachments |
| Auth | **JWT** (access + refresh) in **httpOnly cookies** | |
| Containers | **Docker + docker-compose** | one command runs everything |
| CI | **GitHub Actions** | lint + type-check + test on every PR |

> We run **Python 3.12 inside the backend container** even if your laptop has a newer Python. Don't
> fight your host version — the container is what runs.

---

## 3. Repository structure (fixed — don't reorganize on your own)

```
desklite/
├─ AGENTS.md                 ← this file (the blueprint)
├─ CONTRIBUTING.md           ← how we branch, commit, PR
├─ README.md                 ← how to run the project
├─ docker-compose.yml        ← the one-command bring-up
├─ .env.example              ← documented config (copy to .env)
├─ .github/workflows/ci.yml  ← CI pipeline
├─ .cursor/rules/            ← per-area rules your Cursor agent auto-follows
├─ backend/
│  ├─ app/
│  │  ├─ main.py             ← FastAPI app entry
│  │  ├─ core/              ← config, security, dependencies
│  │  ├─ db/                ← session, base
│  │  ├─ models/           ← SQLAlchemy models
│  │  ├─ schemas/          ← Pydantic schemas
│  │  └─ api/              ← routers (one file per resource)
│  ├─ alembic/             ← migrations
│  └─ tests/
└─ frontend/
   ├─ app/                 ← Next.js App Router pages
   ├─ components/          ← reusable UI components
   ├─ lib/                 ← api client, helpers
   └─ styles/
```

---

## 4. Ownership map — who owns what (avoid stepping on each other)

| Person | Role | Primary area (edit freely) | Coordinate before touching |
|---|---|---|---|
| **Egzona** | Frontend Lead | `frontend/` design system, login/ticket/dashboard UI | shared components |
| **Valza** | Tech Lead | architecture, JWT, RBAC, security, dashboard APIs | DB schema, cross-cutting |
| **Paulina** | Backend / Data | DB, ticket logic, assignment, metrics queries, migrations | `models/`, migrations |
| **Rrezart** | Full-Stack Integration | FE↔BE integration, attachments, search, E2E flows | API contracts |
| **Lis** | DevOps & QA | Docker, CI/CD, testing, monitoring, security testing | `docker-compose`, CI, `.env.example` |

**Golden coordination rules:**
- **DB schema / migrations** → Paulina is the gatekeeper. Only **one** migration merges at a time.
- **API contract** (request/response shape) → agree it in the ticket/PR *before* frontend builds against it.
- **Shared UI components** → Egzona owns the design system; don't fork one-off styles.
- **`.env.example`, `docker-compose.yml`, CI** → Lis is the gatekeeper.

---

## 5. The non-negotiable golden rules (security & correctness)

These prevent the bugs a mentor/client *will* attack in the defense:

1. **Identity comes from the token, never the client.** `requester_id`, `uploader_id`, the current
   user's role — always read from the validated JWT. Never accept them from the request body.
2. **Whitelist writable fields** (mass-assignment defense). Pydantic `Create`/`Update` schemas list
   exactly which fields a client may set. A client can **never** set `id`, `role`, `owner_id`,
   `status` (except via the proper transition endpoint), or timestamps.
3. **Object-level authorization on every read/write by ID.** Before returning or modifying a ticket,
   check the current user is allowed to see it. A Customer requesting someone else's ticket gets
   **403/404**, never the data. (This is our live IDOR demo — it must hold.)
4. **RBAC on every endpoint.** Each route declares which roles may call it; others get **403**.
5. **Passwords are hashed** (Argon2/bcrypt), never stored or logged in plain text.
6. **Parameterized queries only.** Never build SQL with string formatting. Use the ORM / bound params.
7. **Sanitize user content** (comments) to prevent stored XSS.
8. **No secrets in git.** Only `.env.example` is committed. Real values live in `.env` (git-ignored).
9. **Files go to object storage, not the DB.** Downloads use short-lived **signed URLs**; the bucket is never public.

---

## 6. API conventions (so frontend & backend always agree)

- Base path: **`/api/v1`**. Auto docs at **`/docs`**.
- Resources are **plural nouns**: `/api/v1/tickets`, `/api/v1/tickets/{id}/comments`.
- JSON fields are **snake_case** (Python/Pydantic default) on both sides — frontend uses snake_case too. Don't auto-camelCase.
- Status codes: `200` ok, `201` created, `400` bad input, `401` not logged in, `403` not allowed,
  `404` not found, `422` validation error.
- Errors always return `{ "detail": "<message>" }`.
- IDs are **integers** (sequential). Security comes from authorization checks, *not* from hiding IDs —
  this is intentional so we can demo IDOR protection.
- Every list endpoint is **permission-scoped**: it returns only rows the caller may see, then filters/paginates.

---

## 7. Data model (the agreed core — Paulina owns changes)

- **User**(id, email unique, password_hash, role, full_name, created_at)
- **Ticket**(id, title, description, status, priority, requester_id→User, assignee_id→User nullable,
  created_at, updated_at, resolved_at nullable)
- **Comment**(id, ticket_id→Ticket, author_id→User, body, created_at)
- **Attachment**(id, ticket_id→Ticket, uploader_id→User, filename, content_type, size, storage_key, created_at)
- **AuditLog**(id, actor_id→User, ticket_id, action, from_value, to_value, created_at)

Conventions: snake_case plural tables, integer PKs, explicit FKs, `created_at`/`updated_at` on
mutable tables. **Status** ∈ `open` → `in_progress` → `resolved` → `closed` (only valid transitions).
**Priority** ∈ `low`, `medium`, `high`, `urgent`. **Role** ∈ `customer`, `agent`, `admin`.

---

## 8. Coding conventions

**Backend (Python)**
- `snake_case` for functions/variables, `PascalCase` for classes.
- One router file per resource in `app/api/`; keep business logic in `app/services/` or the router, not in models.
- Pydantic schemas: `TicketCreate`, `TicketUpdate`, `TicketRead` — never reuse the DB model as the API shape.
- Format/lint with **ruff**. Type hints everywhere.

**Frontend (TypeScript)**
- `camelCase` variables, `PascalCase` components, files for components in `PascalCase.tsx`.
- **Server Components by default**; add `"use client"` only when you need state/effects/events.
- All API calls go through the typed client in `lib/api.ts` — no scattered `fetch()` calls.
- Use **design tokens** from `tailwind.config.ts` (colors/spacing). No hard-coded hex values in components.
- TypeScript `strict` is on. No `any` without a comment justifying it.

---

## 9. Design system (Egzona owns; everyone uses the tokens)

Use Tailwind tokens, never raw colors:

| Token | Use |
|---|---|
| `brand` | primary actions, links, active nav |
| `status-open / status-progress / status-resolved / status-closed` | ticket status badges |
| `priority-low / -medium / -high / -urgent` | priority badges |
| `surface`, `muted`, `border` | backgrounds, secondary text, dividers |

Every list/form must have **empty**, **loading**, and **error** states. Components must be responsive
and pass a basic accessibility check (labels, focus states, contrast).

---

## 10. Git & workflow (full detail in CONTRIBUTING.md)

- `main` is **protected**: no direct pushes; PR + 1 review + green CI required.
- Branch names: `feature/<area>-<short>`, `fix/<short>`, `chore/<short>` (e.g. `feature/login-ui`).
- Commits: **Conventional Commits** — `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- Keep PRs **small** and linked to a `DESK-` ticket. Update `.env.example` in the *same* PR if you add a config var.
- After a merge: `git pull origin main`, and `docker compose up --build` only if deps/Dockerfiles changed.

---

## 11. Definition of Done (every story)

- [ ] Acceptance criteria from the Jira ticket are met
- [ ] Follows the golden rules (§5) and conventions (§6, §8)
- [ ] Tests added/updated and passing; CI green
- [ ] No secrets committed; `.env.example` updated if needed
- [ ] Reviewed by one teammate via PR

---

## 12. How to start (Sprint 0)

1. **Lis** bootstraps the foundation (this repo, Docker, CI, runnable skeletons). ← *in progress*
2. Everyone installs Docker (`DeskLite_Team_Setup_Guide.docx`), clones, `cp .env.example .env`, `docker compose up`.
3. Then pick up your Sprint 0 stories:
   - Valza → backend skeleton wiring + CI; Paulina → DB connection + Alembic + branch protection;
     Egzona → frontend base + `.env.example`; Rrezart → backend health story + design tokens.
4. From Sprint 1 on, work feature branches → PR → review → merge, always within your ownership area.

> When in doubt: **read this file, follow the golden rules, keep PRs small, ask the team before changing a shared contract.**
