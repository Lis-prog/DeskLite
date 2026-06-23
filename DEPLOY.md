# DeskLite — Production deployment (Contabo VPS)

Deploy the full stack (PostgreSQL, MinIO, FastAPI, Next.js) behind Caddy with HTTPS.

## What you must do manually (cannot be automated in git)

| Step | Where | What to fill in |
|------|--------|-----------------|
| **1. Domain DNS** | Your registrar | A records → VPS IP for `app`, `api`, `files` subdomains |
| **2. Production `.env`** | VPS only | Copy `.env.production.example` → `.env` — passwords, JWT, URLs |
| **3. Caddyfile** | VPS `/etc/caddy/Caddyfile` | Replace `yourdomain.com` with your real domain |
| **4. GitHub secrets** (optional CD) | Repo Settings → Secrets | `VPS_HOST`, `VPS_SSH_USER`, `VPS_SSH_KEY` |

---

## VPS specs (minimum met)

Your Contabo VPS (4 vCPU, 8 GB RAM) is sufficient for all services on one host.

---

## First-time server setup

SSH in (PowerShell):

```powershell
ssh root@YOUR_VPS_IP
```

### 1. System update + firewall

```bash
apt update && apt upgrade -y
apt install -y ufw docker.io docker-compose-v2 git
systemctl enable docker

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 2. Deploy user (recommended)

```bash
adduser desklite
usermod -aG docker desklite
# Add your SSH public key to /home/desklite/.ssh/authorized_keys
```

### 3. Install Caddy (HTTPS)

```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy
```

### 4. Configure Caddy

```bash
sudo cp deploy/Caddyfile.example /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile   # ← EDIT: replace yourdomain.com
sudo systemctl reload caddy
```

### 5. Clone repo + production env

```bash
su - desklite
git clone https://github.com/Lis-prog/DeskLite.git
cd DeskLite
cp .env.production.example .env
nano .env                         # ← EDIT: all REPLACE_* values + your HTTPS URLs
```

Generate secrets (on VPS):

```bash
openssl rand -hex 32   # use for JWT_SECRET
openssl rand -hex 16   # use for POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD
```

**Critical `.env` values:**

```env
FRONTEND_ORIGIN=https://app.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
S3_PUBLIC_ENDPOINT=https://files.yourdomain.com
COOKIE_SECURE=true
APP_ENV=production
```

### 6. First deploy

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

Optional demo data:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python seed.py
```

---

## Deploy updates (after code merges)

On the VPS:

```bash
cd ~/DeskLite
./deploy/deploy.sh
```

Or trigger **Actions → Deploy → Run workflow** (after GitHub secrets are set).

---

## Architecture

```
Internet → Caddy (:443)
            ├── app.*  → frontend :3000 (localhost only)
            ├── api.*  → backend  :8000 (localhost only)
            └── files.* → minio   :9000 (localhost only, presigned downloads)

Docker internal network:
  db (Postgres) · minio · backend · frontend
  (5432 and MinIO console NOT exposed publicly)
```

---

## Smoke test checklist

- [ ] `curl https://api.yourdomain.com/api/v1/health` → `{"status":"ok"}`
- [ ] Open `https://app.yourdomain.com` → login page
- [ ] Login as admin → create ticket → assign → resolve → **Resolved** date shows
- [ ] Upload attachment → **Download** works (tests `S3_PUBLIC_ENDPOINT`)
- [ ] Swagger **disabled** on production API (`/docs` → 404)

---

## Health checks & uptime monitoring

Downtime is detectable at three layers:

- **Health endpoints** (backend):
  - `GET /api/v1/health` — liveness; always `200` while the process is up.
  - `GET /api/v1/health/db` — readiness; returns `200` when Postgres is reachable
    and **`503`** when it is not, so monitors can detect downtime from the status
    code alone.
- **Container healthchecks** — `backend` and `frontend` declare Docker
  `healthcheck`s (alongside the existing `db`/`minio` ones) in
  `docker-compose.yml`, so they apply in dev and production. Check status with
  `docker compose ps` (look for `healthy` / `unhealthy`).
- **Uptime monitor** — `.github/workflows/uptime.yml` runs on a schedule
  (every 15 min) and on demand, probing the live `/api/v1/health` and
  `/api/v1/health/db` endpoints. A failed run signals downtime (GitHub notifies
  on failed scheduled runs). Set the repository **variable** `HEALTHCHECK_URL`
  (e.g. `https://api.yourdomain.com`) to enable it; while unset the job skips
  cleanly so it never raises false alarms.

## Local dev (unchanged)

```bash
docker compose up --build
```

Uses dev overrides: hot reload, volume mounts, localhost URLs.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Login fails after HTTPS | `COOKIE_SECURE=true`, `FRONTEND_ORIGIN` exact match |
| Missing security headers | Production sets HSTS via Caddy + app middleware (`APP_ENV=production`) |
| CORS errors | `FRONTEND_ORIGIN` must match browser URL (https, no trailing slash) |
| Attachment download 404 | `S3_PUBLIC_ENDPOINT` + Caddy `files.*` block must match |
| Frontend calls wrong API | Rebuild frontend: `NEXT_PUBLIC_API_URL` is set at **build** time |
| DB connection refused | `DATABASE_URL` host must be `db`, not `localhost` |

---

## Files added for production

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | No dev mounts, localhost ports, prod commands |
| `frontend/Dockerfile` | Multi-stage: `development` / `production` |
| `.env.production.example` | Server env template |
| `deploy/Caddyfile.example` | HTTPS reverse proxy |
| `deploy/deploy.sh` | Pull, build, migrate, up |
| `.github/workflows/deploy.yml` | Optional manual CD |
