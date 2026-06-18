# DeskLite — Role & Permission Matrix

> Owner: Valza Dalipi (Tech Lead, security). This is the **single source of truth** for what
> each role may do. Code in `backend/app/core/dependencies.py` (`require_roles`) and
> `backend/app/core/permissions.py` (object-level checks) must match this table. Change the
> table here first, then the code.

## Roles

| Role | Description |
|---|---|
| `customer` | Default role for every newly registered user. |
| `agent` | Support staff who work tickets assigned to them. |
| `admin` | Managers; full visibility and assignment control. |

A user's role is **assigned by an admin**, never chosen at sign-up. Registration always creates a `customer`.

## Endpoint permissions (RBAC)

| Endpoint | customer | agent | admin |
|---|:--:|:--:|:--:|
| `POST /api/v1/auth/register` | public | public | public |
| `POST /api/v1/auth/login` | public | public | public |
| `POST /api/v1/auth/logout` | yes | yes | yes |
| `POST /api/v1/auth/refresh` | yes | yes | yes |
| `GET /api/v1/auth/me` | yes | yes | yes |
| `GET /api/v1/auth/admin/ping` | 403 | 403 | yes |
| `GET /api/v1/health`, `/health/db` | public | public | public |
| `GET /api/v1/health/authed` | yes | yes | yes |
| `GET /api/v1/admin/users` | 403 | 403 | yes |
| `PATCH /api/v1/admin/users/{id}/role` | 403 | 403 | yes |
| `POST /api/v1/tickets` | yes | yes | yes |
| `GET /api/v1/tickets` | yes | yes | yes |
| `GET /api/v1/tickets/{id}` | yes | yes | yes |
| `PATCH /api/v1/tickets/{id}` | yes* | yes* | yes* |
| `GET /api/v1/tickets/{id}/comments` | yes* | yes* | yes* |
| `POST /api/v1/tickets/{id}/comments` | yes* | yes* | yes* |
| `POST /api/v1/tickets/{id}/attachments` | yes* | yes* | yes* |
| `GET /api/v1/tickets/{id}/satisfaction` | yes* | yes* | yes* |
| `POST /api/v1/tickets/{id}/satisfaction` | yes** | 403 | 403 |
| `PATCH /api/v1/admin/tickets/{id}/assignee` | 403 | 403 | yes |

\* Route is open to every authenticated role, but **object-level scope** applies
(same rules as ticket by-ID). Callers who may not access the ticket get **403**.

\** Only the ticket **requester** may submit satisfaction feedback, and only when
the ticket status is **closed**.

List and by-ID ticket routes are open to every authenticated role; **which rows**
are returned is enforced by object-level scope (see table below): customer → own
(`requester_id`), agent → assigned (`assignee_id`), admin → all.

"yes" = allowed when authenticated. "public" = no token required. "403" = forbidden
for an authenticated caller; an unauthenticated caller always gets **401**.

RBAC is enforced with `require_roles(...)` from `app/core/dependencies.py`. Admin-only
routes live under the `/admin` router, which declares `require_roles("admin")` at the
router level so every current and future route under it is gated by construction.

## Object-level access (ownership, IDOR defense)

Beyond "is this role allowed to call the route", every by-ID resource access is checked against
ownership. Implemented in `can_access_ticket()` / `ensure_ticket_access()`.

| Resource | customer | agent | admin |
|---|---|---|---|
| Ticket | only where `requester_id == user.id` | only where `assignee_id == user.id` | all tickets |
| Comment (on ticket) | same as parent ticket | same as parent ticket | same as parent ticket |
| Attachment (on ticket) | same as parent ticket | same as parent ticket | same as parent ticket |
| Satisfaction rating | submit only as requester on **closed** ticket; read if ticket visible | read if ticket visible | read if ticket visible |

A request for a row the caller may not see returns **403** (or 404), never the data.

## Golden rules these checks enforce (see `AGENTS.md` §5)

1. Identity (`user.id`, `role`) comes from the validated JWT, never the request body.
2. Role is whitelisted out of `UserCreate` — a client cannot self-assign `agent`/`admin`.
3. RBAC (role allowed?) **and** ownership (may this user see this row?) are both checked on by-ID access.
