# Architecture Decision Records — DeskLite

> Owner: Valza Dalipi (Tech Lead).  
> Each ADR captures *why* we chose something so future-us doesn't re-litigate it.  
> Format: status · context · decision · consequences.

---

## ADR-001 — JWT in httpOnly cookies (not Authorization header)

**Status:** Accepted  
**Date:** Sprint 0

**Context:**  
We needed a stateless auth mechanism. Two common options: `Authorization: Bearer` header (requires JS to store the token) or httpOnly cookies (browser stores the token, JS cannot touch it).

**Decision:**  
Store both the access token and refresh token in **httpOnly, SameSite=Lax cookies**. The API reads `Cookie: access_token=…`; the frontend never sees the raw token value.

**Consequences:**  
- ✅ Eliminates XSS token-theft (JS cannot read httpOnly cookies).  
- ✅ Cookies are sent automatically by the browser on same-origin requests.  
- ✅ `credentials: "include"` in `lib/api.ts` is the only frontend change needed.  
- ⚠️ CSRF is a concern — mitigated by `SameSite=Lax` and validating `Origin` header on state-changing requests.  
- ⚠️ Mobile clients that don't support cookies need a separate strategy (out of scope for v1).

---

## ADR-002 — Identity from JWT, never from request body

**Status:** Accepted  
**Date:** Sprint 0

**Context:**  
A naive implementation might accept `requester_id` in the POST body and trust it. This is a mass-assignment / privilege-escalation vulnerability: any user could claim to be someone else.

**Decision:**  
Every endpoint that needs the current user's identity calls `Depends(get_current_user)`. The dependency decodes the JWT and returns a validated User object. No endpoint ever reads `user_id`, `role`, or `owner_id` from the request body for identity purposes.

**Consequences:**  
- ✅ Eliminates the entire class of "I can set my own role" attacks.  
- ✅ Single place to audit: `app/core/dependencies.py`.  
- ✅ Pydantic `Create`/`Update` schemas simply omit these fields — clients can't even send them.

---

## ADR-003 — Integer PKs + authorization-not-obscurity for IDOR protection

**Status:** Accepted  
**Date:** Sprint 0

**Context:**  
Some systems use UUIDs to make IDs hard to guess, treating obscurity as a security layer. We considered this vs. integer PKs with strict authorization checks.

**Decision:**  
Use **integer PKs**. Protect against IDOR purely through **authorization checks** on every by-ID endpoint: verify the requesting user owns or is permitted to see the resource. Return `403` or `404` on failure — never the data.

**Consequences:**  
- ✅ Simpler queries, foreign keys, and joins.  
- ✅ Forces us to actually implement authorization correctly rather than relying on ID obscurity.  
- ✅ We can demo a live IDOR attempt in the defense: request ticket `id=1` as another user → 403.  
- ⚠️ IDs are sequential and enumerable — this is intentional and acceptable because auth is the real guard.

---

## ADR-004 — PostgreSQL CHECK constraints + app-layer enum validation (dual guard)

**Status:** Accepted  
**Date:** Sprint 0

**Context:**  
`status`, `priority`, and `role` columns accept only specific string values. We could validate only in Pydantic, only in the DB, or in both.

**Decision:**  
Validate in **both layers**:  
1. Pydantic schemas use `Literal` / `Enum` types — invalid values are rejected at the API boundary with a `422`.  
2. The migration adds `CHECK` constraints — invalid values are rejected at the DB layer even if something bypasses Pydantic.

**Consequences:**  
- ✅ Defense in depth: a bug in one layer doesn't corrupt data.  
- ✅ DB self-documents what values are valid, independent of application code.  
- ⚠️ Adding a new status/priority value requires both a Pydantic change and a migration — small cost, worth the safety.

---

## ADR-005 — Alembic for all schema changes; one migration merges at a time

**Status:** Accepted  
**Date:** Sprint 0

**Context:**  
With five developers, two people could create conflicting migrations simultaneously (same `down_revision`), corrupting the migration chain.

**Decision:**  
- All schema changes go through an Alembic migration — no ad-hoc `CREATE TABLE` or `ALTER TABLE`.  
- **Paulina is the gatekeeper**: only one migration PR merges at a time. The next migration can only start after the previous one is in `main` and `alembic upgrade head` has been run.  
- Migration files are named `NNN_<slug>.py` with an incrementing prefix so order is visually obvious.

**Consequences:**  
- ✅ Clean, auditable migration history.  
- ✅ `alembic downgrade -1` is always available for rollback.  
- ⚠️ Slightly slower iteration — worth it to avoid merge-conflict hell in `versions/`.

---

## ADR-006 — MinIO (S3-compatible) for file storage; signed URLs for downloads

**Status:** Accepted  
**Date:** Sprint 0

**Context:**  
Attachments could be stored in PostgreSQL (as bytea/large objects) or in object storage. The bucket could be public or access could be controlled via signed URLs.

**Decision:**  
Files go to **MinIO** (S3-compatible, runs in Docker). The bucket is **private**. Downloads are served via **short-lived pre-signed URLs** generated by the backend — the frontend never gets a permanent public URL.

**Consequences:**  
- ✅ DB stays lean — no binary blobs in Postgres.  
- ✅ Signed URLs expire (default: 15 min) so a leaked URL is time-limited.  
- ✅ In production, MinIO is swappable for AWS S3 with zero code changes (same boto3 API).  
- ⚠️ Local dev requires the `minio` Docker container to be running — handled by `docker-compose.yml`.

---

## ADR-007 — Coverage floor at 80 % enforced in CI

**Status:** Accepted  
**Date:** Sprint 0

**Context:**  
Without a coverage gate, test coverage tends to drift downward as features are added under time pressure.

**Decision:**  
`pytest --cov-fail-under=80` in CI. PRs that drop coverage below 80 % fail the `Backend` check and cannot merge until tests are added.

**Consequences:**  
- ✅ Coverage cannot silently erode.  
- ✅ Forces every new endpoint to ship with at least a smoke test.  
- ⚠️ 80 % is a floor, not a target — aim higher on security-critical paths (auth, RBAC, IDOR).
