# DeskLite — OWASP Top 10 (2021) Mapping Checklist

> Owner: Egzona Haskuka. Security Hardening (Sprint 3). This checklist maps each
> relevant [OWASP Top 10 (2021)](https://owasp.org/Top10/) risk to the concrete
> mitigation **we actually implemented** in DeskLite, with pointers to the code
> and tests that enforce it. Keep it honest: anything not yet built is marked
> **Partial** or **Planned** so we never claim coverage we don't have.

## Status legend

| Status | Meaning |
|---|---|
| ✅ Mitigated | A control is implemented and covered by code (and usually tests). |
| 🟡 Partial | Core control is in place; a related hardening item is still planned. |
| ⚪ N/A | The risk has no meaningful attack surface in DeskLite today. |

## Summary

| # | Risk | Status | Primary mitigation |
|---|---|:--:|---|
| A01 | Broken Access Control | ✅ | RBAC + object-level ownership checks; identity from JWT, never the body |
| A02 | Cryptographic Failures | ✅ | bcrypt password hashing; signed JWTs; httpOnly/Secure cookies; private bucket via signed URLs |
| A03 | Injection | ✅ | SQLAlchemy parameterized queries; Pydantic validation; comment HTML sanitization |
| A04 | Insecure Design | ✅ | Status state machine; RBAC-by-construction; least-privilege defaults; permission matrix as source of truth |
| A05 | Security Misconfiguration | ✅ | Security headers; CORS locked to one origin; Swagger off in prod; secrets via env |
| A06 | Vulnerable & Outdated Components | 🟡 | `pip-audit` + `npm audit` in CI; pinned versions and lockfiles |
| A07 | Identification & Authentication Failures | 🟡 | bcrypt, access+refresh JWTs, generic 401s; auth rate limiting still planned |
| A08 | Software & Data Integrity Failures | 🟡 | CI gates + branch protection + lockfiles; no artifact signing yet |
| A09 | Security Logging & Monitoring Failures | 🟡 | Audit log of status/assignment changes; centralized monitoring is Sprint 4 |
| A10 | Server-Side Request Forgery (SSRF) | ⚪ | No user-controlled outbound requests; egress only to a fixed storage endpoint |

---

## A01 — Broken Access Control ✅

The highest-priority risk for a ticketing app, addressed at two layers:

- **RBAC (is this role allowed to call the route?)** — `require_roles(...)` gates
  endpoints; admin-only routes sit under a router that declares
  `require_roles("admin")` so every current and future child route is gated by
  construction. See `backend/app/core/dependencies.py`, `backend/app/api/admin.py`.
- **Object-level authorization (may this user see this row?)** — `can_access_ticket()`
  / `ensure_ticket_access()` and `scoped_ticket_query()` enforce ownership:
  customer → own (`requester_id`), agent → assigned (`assignee_id`), admin → all.
  See `backend/app/core/permissions.py`.
- **Identity comes from the validated JWT**, never the request body
  (`get_current_user` reads `sub`/`role` from the token).
- **Privilege escalation blocked** — `role` is whitelisted out of `UserCreate`;
  registration always creates a `customer`; role can only change via the dedicated
  admin endpoint (`backend/app/schemas/user.py`, `backend/app/api/auth.py`).
- **List filters never widen scope** — query params combine with AND on top of the
  role scope (`backend/app/services/ticket_query.py`).

Evidence: `backend/tests/test_permissions.py`, `test_attachment_downloads.py`
(cross-user/IDOR → 403/404), `test_admin.py`, `test_ticket_status_transition.py`.
Source of truth: `.github/docs/architecture/permission-matrix.md`.

## A02 — Cryptographic Failures ✅

- **Passwords** are hashed with **bcrypt** and never stored or returned in plaintext
  (`hash_password`/`verify_password` in `backend/app/core/security.py`); `UserRead`
  never exposes `password_hash`.
- **Tokens** are signed JWTs (HS256) with the secret loaded from the environment
  (`backend/app/core/config.py`); `decode_token` validates signature and token type.
- **Cookies** carrying tokens are `httpOnly`, `SameSite=Lax`, and `Secure` in any
  HTTPS environment (`cookie_secure`); access tokens are short-lived (15 min) with
  refresh rotation (`backend/app/api/auth.py`).
- **HSTS** is sent in production (`backend/app/core/security_headers.py`).
- **Attachments stay private** — downloads use short-lived (5 min) presigned URLs,
  so the object bucket never needs public access
  (`backend/app/core/storage.py`, `DOWNLOAD_URL_EXPIRY_SECONDS`).

Evidence: `backend/tests/test_auth.py`, `test_attachment_downloads.py`,
`test_production_config.py`.

## A03 — Injection ✅

- **SQL injection** — all data access goes through SQLAlchemy with bound parameters;
  no string-built SQL. Full-text search (`q`) is parameterized and case-insensitive
  (`backend/app/services/ticket_query.py`).
- **Input validation** — Pydantic schemas whitelist writable fields and reject
  malformed payloads before they reach the DB (`backend/app/schemas/`).
- **Stored XSS** — comment text is stripped of HTML/script markup before storage as
  defense-in-depth, and rendered as plain text in the UI
  (`backend/app/core/sanitize.py`).

Evidence: `backend/tests/test_sanitize.py`, `test_ticket_schemas.py`,
`test_ticket_query.py`.

## A04 — Insecure Design ✅

- **Ticket lifecycle state machine** allows only valid transitions
  (`open → in_progress → resolved → closed`) and rejects illegal ones
  (`backend/app/core/ticket_state.py`).
- **Least privilege by default** — new accounts are always `customer`; sensitive
  actions require explicit roles.
- **Security baked into the design** — RBAC enforced at the router level, and the
  permission matrix is the agreed single source of truth that code must match.

Evidence: `backend/tests/test_ticket_state.py`, `test_ticket_status_transition.py`.

## A05 — Security Misconfiguration ✅

- **Security headers** on every response: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, plus HSTS in
  production (`backend/app/core/security_headers.py`).
- **CORS** is restricted to the single configured `FRONTEND_ORIGIN` with credentials,
  not a wildcard (`backend/app/main.py`).
- **API docs disabled in production** — Swagger UI and `openapi.json` are off when
  `APP_ENV=production` (`backend/app/main.py`).
- **Secrets via environment** — `.env.example` documents every variable, real values
  stay out of git, and `.gitignore` excludes env files
  (`backend/app/core/config.py`).
- **Generic error messages** avoid leaking internals (e.g. login returns a single
  "Invalid email or password").

Evidence: `backend/tests/test_security_headers.py`, `test_production_config.py`.

## A06 — Vulnerable and Outdated Components 🟡

- **CI dependency scanning** runs on every push/PR: `pip-audit` for Python and
  `npm audit --audit-level=high` for Node, in the dedicated `security` job
  (`.github/workflows/ci.yml`).
- Dependencies are pinned and lockfiles committed for reproducible installs.

Planned: scheduled re-scans / automated upgrade PRs (e.g. Dependabot) are not yet
configured.

## A07 — Identification and Authentication Failures 🟡

- **Strong credential storage** (bcrypt) and a minimum password length of 8
  (`backend/app/schemas/user.py`).
- **Session management** via signed access + refresh JWTs with rotation, httpOnly
  cookies, and strict token-type checks.
- **Anti-enumeration** — login failures always return a generic 401 regardless of
  whether the email exists (`backend/app/api/auth.py`).

Planned: **rate limiting / brute-force throttling** on authentication endpoints is
tracked separately (Sprint 3 Security Hardening, owned by Lis) and is **not yet
merged**. Until then, this risk is only partially mitigated.

Evidence: `backend/tests/test_auth.py`.

## A08 — Software and Data Integrity Failures 🟡

- **CI quality gates** — every PR must pass lint, type-check, and tests (with a
  coverage threshold) before merge; `main` is branch-protected and requires review
  (`.github/workflows/ci.yml`, `CONTRIBUTING.md`).
- **Dependency integrity** — lockfiles pin exact versions; the `security` job audits
  them on each run.

Planned: build artifact signing / provenance (SLSA) is out of scope for the current
phase.

## A09 — Security Logging and Monitoring Failures 🟡

- **Audit trail** — every ticket status change and assignment change records who,
  what (before/after), and when (`backend/app/services/audit.py`,
  `backend/app/models/audit_log.py`).

Planned: centralized error tracking (Sentry) and structured request tracing with
correlation IDs are Sprint 4 deliverables and not yet implemented.

Evidence: `backend/tests/test_resolution_and_audit.py`.

## A10 — Server-Side Request Forgery (SSRF) ⚪

DeskLite does not fetch user-supplied URLs server-side. The only server-initiated
network egress is to the **fixed, env-configured** MinIO/S3 endpoint; file uploads
are streamed to that storage rather than fetched from a client-provided address
(`backend/app/core/storage.py`). There is no current SSRF surface to exploit. This
will be re-evaluated if any feature later fetches remote URLs (e.g. avatar-by-URL,
webhooks).

---

## How to keep this current

When a security control is added or changed, update both the **Summary** table and
the relevant section here, and flip a 🟡/⚪ to ✅ once the control (and its tests)
land. This file is documentation only — it does not change application behavior.
