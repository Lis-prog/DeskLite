# DeskLite — Demo script & runbook

Step-by-step guide for presenting DeskLite locally or on staging.  
Estimated time: **15–20 minutes** (full walkthrough) or **8 minutes** (security-focused cut).

## Before you start

### 1. Start the stack

```bash
cp .env.example .env          # Windows: copy .env.example .env
docker compose up --build -d
```

Wait until all services are healthy:

- App: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

### 2. Load demo data

```bash
docker compose exec backend python seed.py
```

The script is idempotent — safe to re-run. It prints credentials for any **newly created** users.

### 3. Demo accounts (from `backend/seed.py`)

| Role | Name | Email | Password |
|------|------|-------|----------|
| Admin | Alice Admin | `admin@desklite.dev` | `Admin1234!` |
| Agent | Agent Bob | `agent@desklite.dev` | `Agent1234!` |
| Agent | Agent Sara | `agent2@desklite.dev` | `Agent1234!` |
| Customer | Carol Customer | `customer@desklite.dev` | `Customer1234!` |
| Customer | Dan Developer | `customer2@desklite.dev` | `Customer1234!` |

Seed tickets span all statuses. Examples useful during the demo:

| Title | Requester | Assignee | Status |
|-------|-----------|----------|--------|
| Cannot log in to the portal | Carol | — | open |
| Invoice PDF is blank | Dan | — | open |
| Email notifications not arriving | Carol | Agent Bob | in_progress |
| Dashboard loads slowly | Dan | Agent Sara | closed |

---

## Full demo flow

### Act 1 — Customer raises and tracks a ticket (~4 min)

**Login:** `customer@desklite.dev` / `Customer1234!`  
**Lands on:** My Tickets (`/tickets`)

1. Point out Carol only sees **her own** tickets (not Dan's "Invoice PDF is blank").
2. Click **New Ticket**, create a ticket (e.g. "Demo: VPN drops every hour", priority **high**).
3. Open the new ticket — show description, status badge, SLA/overdue indicator.
4. Add a **comment** on the ticket thread.
5. Optional: upload a small **attachment** (PNG or PDF under size limit).

**Talking point:** Registration always creates a `customer`; roles are assigned by admins, never self-selected.

---

### Act 2 — Agent works the queue (~4 min)

**Logout → Login:** `agent@desklite.dev` / `Agent1234!`  
**Lands on:** My Queue (`/tickets/queue`)

1. Show the queue contains only tickets **assigned to Agent Bob** (not Sara's or unassigned pool).
2. Open **Email notifications not arriving** (in progress).
3. Change status via **Ticket status controls** (e.g. `in_progress` → `resolved`).
4. Add an agent comment explaining the fix.

**Talking point:** Agents cannot change status on tickets they are not assigned to — the API returns **403**.

Try as Bob on an unassigned open ticket (Carol's "Cannot log in to the portal"): status change should be blocked.

---

### Act 3 — Admin overview and assignment (~5 min)

**Logout → Login:** `admin@desklite.dev` / `Admin1234!`  
**Lands on:** Dashboard (`/dashboard`)

1. **KPI cards** — total tickets, open, in progress, unassigned (aggregated server-side, role-scoped).
2. **Charts** — breakdown by status and priority.
3. **Agent workload** — active ticket count per agent (`open` + `in_progress` only).
4. **Resolution time** — average/median seconds for resolved tickets.
5. Go to **All Tickets** — admin sees every ticket; use filters (status, priority, search).
6. Open an **unassigned** ticket (e.g. Dan's "Invoice PDF is blank").
7. **Assign** the ticket to Agent Sara from the ticket detail page.
8. Optional: open a **closed** ticket and show satisfaction rating (seed data on closed tickets).

**Talking point:** Metrics use the same visibility rules as ticket lists — customers and agents never see org-wide numbers in the API.

---

### Act 4 — Live IDOR defense (~5 min)

DeskLite uses **integer primary keys** and blocks unauthorized access with **authorization checks**, not security through obscurity (see [ADR-003](../.github/docs/architecture/ADR.md)).

#### Setup (30 seconds)

While still logged in as **admin**, open **All Tickets** and note the numeric ID of a ticket Carol does **not** own — e.g. Dan's **Invoice PDF is blank**.  
Write it down as `{VICTIM_ID}`.

#### Demo A — Browser (UI)

1. **Logout → Login** as `customer@desklite.dev`.
2. Confirm Carol's list does not include Dan's ticket.
3. Manually navigate to `http://localhost:3000/tickets/{VICTIM_ID}`.

**Expected:** Error state — *"Could not load ticket"* / access denied message. **No ticket title or description leaks.**

#### Demo B — API (Swagger or curl)

**Swagger:** http://localhost:8000/docs

1. `POST /api/v1/auth/login` with Carol's credentials.
2. `GET /api/v1/tickets/{VICTIM_ID}` using the session cookie.

**Expected:** HTTP **403** with a generic forbidden detail — never the victim's data.

**curl (copy-paste friendly):**

```bash
# Log in as Carol; save session cookie
curl -s -c /tmp/dl-cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"customer@desklite.dev","password":"Customer1234!"}'

# Replace 99 with {VICTIM_ID} from the admin step
curl -s -b /tmp/dl-cookies.txt -w "\nHTTP %{http_code}\n" \
  http://localhost:8000/api/v1/tickets/99
```

On Windows PowerShell, use a cookies file path such as `$env:TEMP\dl-cookies.txt`.

#### Demo C — Metrics scope (optional, 1 min)

Still as Carol:

```bash
curl -s -b /tmp/dl-cookies.txt http://localhost:8000/api/v1/metrics/tickets
```

Compare counts with the same call after logging in as admin. Carol's `total` reflects **only her tickets**.

**Talking points:**

- RBAC (role allowed?) **and** object-level scope (may this user see this row?) are both enforced.
- Regression suite: `backend/tests/test_idor.py`.
- Permission matrix: [`.github/docs/architecture/permission-matrix.md`](../.github/docs/architecture/permission-matrix.md).

---

## Shortcuts (time-boxed presentations)

| Focus | Acts | Time |
|-------|------|------|
| End-to-end product | 1 → 2 → 3 (skip IDOR) | ~12 min |
| Security / OWASP | Act 4 only (+ 2 min setup) | ~7 min |
| Manager dashboard | Act 3 only | ~5 min |

---

## Staging / production demo

For a live VPS deploy, use the same flow with your public URLs:

- Set `NEXT_PUBLIC_API_URL` and CORS origins per `DEPLOY.md`.
- Run `docker compose exec backend python seed.py` on the server **once** (do not re-seed production with default passwords in real deployments).
- Use `https://app.yourdomain.com` and `https://api.yourdomain.com/docs`.

---

## Troubleshooting during a demo

| Problem | Fix |
|---------|-----|
| Login fails on localhost | Ensure `.env` has `COOKIE_SECURE=false` for HTTP |
| Empty ticket list after seed | Re-run `seed.py`; check `docker compose logs backend` |
| 403 on own ticket | Wrong user for that ticket's requester/assignee |
| Dashboard empty / error | Must be logged in as **admin** |
| Port already in use | `docker compose down` then restart, or free ports 3000/8000 |

---

## After the demo

```bash
docker compose down        # stop services
docker compose down -v     # stop + wipe database (fresh start next time)
```

---

## Related docs

- [README.md](../README.md) — local setup and test commands
- [DEPLOY.md](../DEPLOY.md) — production deployment
- [Permission matrix](../.github/docs/architecture/permission-matrix.md) — roles and endpoints
- [ADR-003](../.github/docs/architecture/ADR.md) — IDOR design decision
