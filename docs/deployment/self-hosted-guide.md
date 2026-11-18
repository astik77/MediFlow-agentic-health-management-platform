# MEDIFLOW — Self-Hosted Personal Deployment Guide (Option A)

Deploy the complete privacy-first MEDIFLOW stack (**Caddy Reverse Proxy + Next.js + FastAPI + PostgreSQL 16/pgvector + Ollama**) on a single VPS, mini-PC, or home server with **zero third-party APIs or external data sharing**.

---

## 1. Recommended Hardware

| Tier | Specs | Experience |
|---|---|---|
| **Minimum (4 GB RAM)** | 2 vCPU, 4 GB RAM, 25 GB SSD | Full app + RapidOCR + `qwen2.5:1.5b` + `nomic-embed-text` |
| **Recommended (8 GB RAM)** | 2–4 vCPU, 8 GB RAM, 40 GB SSD | Smooth concurrent OCR, Hybrid RAG, and faster Ollama responses |

Works great on Ubuntu 24.04 LTS / Debian 12 VPS (e.g., Hetzner, DigitalOcean, Oracle Cloud Always-Free ARM) or a home server accessed privately over **Tailscale**.

**Prerequisite on server:** Docker Engine + Docker Compose v2 (`docker compose version`).

---

## 2. Architecture Overview

```
Browser (HTTPS :443 / HTTP :80)
          │
          ▼
   ┌─────────────┐
   │   Caddy 2   │  ← ONLY container exposed to the host/internet
   └──────┬──────┘
    ┌─────┴─────┐
    ▼           ▼
 /api/*       /* (UI)
┌────────┐  ┌────────┐
│FastAPI │  │Next.js │
│ :8000  │  │ :3000  │
└───┬──┬─┘  └────────┘
    │  │
    ▼  ▼
┌──────┐ ┌────────┐
│PG 16 │ │ Ollama │  (all private on mediflow_prod_net)
│pgvec │ │ :11434 │
└──────┘ └────────┘
```

- **Same-origin routing:** Caddy serves both the UI and `/api/*` under one origin, keeping `HttpOnly` + `SameSite=lax` session cookies secure with zero CORS friction.
- **Persistent volumes:** Database (`mediflow_prod_pg_data`), uploaded medical documents (`mediflow_prod_uploads_data`), Ollama models (`mediflow_prod_ollama_data`), and TLS certificates (`mediflow_prod_caddy_data`) survive container restarts and upgrades.
- **Automatic migrations & model pulls:** The `api` container runs `alembic upgrade head` on startup, and `ollama-init` automatically pulls `qwen2.5:1.5b` and `nomic-embed-text` on first boot.

---

## 3. Step-by-Step Deployment (4 Commands)

### Step 1 — Clone the Repository on Your Server
```bash
git clone https://github.com/astik77/MediFlow-agentic-health-management-platform.git mediflow
cd mediflow
```

### Step 2 — Create `.env.prod` and Generate Secrets
```bash
cp .env.prod.example .env.prod
```

Generate strong random credentials:
```bash
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24)); print('SECRET_KEY=' + secrets.token_hex(64)); print('CSRF_SECRET=' + secrets.token_hex(32))"
```

Edit `.env.prod` (`nano .env.prod`) and paste those generated values.

**Choose your access mode in `.env.prod`:**
- **Custom Domain with Auto-HTTPS (Recommended for VPS):**
  Point your domain's DNS `A` record to your server IP, open ports `80` and `443` in your firewall, and set:
  ```env
  MEDIFLOW_SITE_ADDRESS=health.yourdomain.com
  CORS_ORIGINS=["https://health.yourdomain.com"]
  COOKIE_SECURE=true
  ```
  Caddy will automatically obtain and renew a free Let's Encrypt TLS certificate!
- **Private LAN / Localhost / Tailscale IP (No Public Domain):**
  Keep the defaults (or add your LAN/Tailscale IP to `CORS_ORIGINS`):
  ```env
  MEDIFLOW_SITE_ADDRESS=:80
  CORS_ORIGINS=["http://localhost","http://100.x.y.z"]
  COOKIE_SECURE=false
  ```

### Step 3 — Build and Launch the Stack
**If Ollama is already installed on your host PC** (`OLLAMA_BASE_URL=http://host.docker.internal:11434`):
```bash
docker compose -f docker-compose.prod.yaml --env-file .env.prod up -d --build
```
**On a fresh VPS (run bundled Ollama inside Docker + auto-pull models):**
Set `OLLAMA_BASE_URL=http://ollama:11434` in `.env.prod`, then run:
```bash
docker compose -f docker-compose.prod.yaml --profile bundled-ollama --env-file .env.prod up -d --build
```

### Step 4 — Verify Everything Is Healthy
```bash
docker compose -f docker-compose.prod.yaml ps
```
Check model pull progress on first boot (~1.3 GB one-time download):
```bash
docker logs -f mediflow_prod_ollama_init
```
Then open **`https://health.yourdomain.com`** (or **`http://localhost`**) and register your personal patient account!

---

## 4. Backups & Maintenance

### Backup PostgreSQL Database
```bash
docker exec mediflow_prod_postgres pg_dump -U mediflow mediflow_db | gzip > mediflow_db_$(date +%F).sql.gz
```

### Backup Uploaded Medical Documents
```bash
docker run --rm -v mediflow_prod_uploads_data:/data:ro -v "$(pwd)":/backup alpine \
  tar czf /backup/mediflow_uploads_$(date +%F).tar.gz -C /data .
```

### Update to a Newer Version of MEDIFLOW
```bash
git pull origin main
docker compose -f docker-compose.prod.yaml --env-file .env.prod up -d --build
```
*(Migrations run automatically on `api` startup; all volumes remain intact.)*

### Stop Stack Cleanly (Preserving Data)
```bash
docker compose -f docker-compose.prod.yaml down
```
