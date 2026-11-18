# MEDIFLOW — Self-Hosted CI/CD Setup Guide

MEDIFLOW includes an end-to-end **GitHub Actions CI/CD pipeline** designed for your self-hosted Docker deployment:

1. **Continuous Integration (`.github/workflows/ci.yml`)** — Runs on every push and pull request to `main`:
   - Backend `ruff` lint + full `pytest` suite against PostgreSQL 16 + `pgvector`
   - Frontend `pnpm type-check`, `pnpm lint`, and `pnpm build`
2. **Continuous Deployment (`.github/workflows/cd.yml`)** — Triggers automatically whenever **MediFlow CI** succeeds on `main` (or manually via **Actions → MediFlow CD (Self-Hosted) → Run workflow**):
   - Pulls `origin/main` in your local deployment directory
   - Runs `scripts/deploy.ps1`, which inspects changed files and rebuilds **only** the affected Docker containers (`web`, `api`, or full stack) using `docker-compose.prod.yaml` and `.env.prod`
   - Verifies HTTP 200 health checks on `http://localhost/api/v1/health` and `http://localhost/`

---

## One-Time Setup (Connect Your Machine to GitHub Actions)

Because your production stack runs locally on your machine (`http://localhost`), GitHub's cloud servers cannot push directly to it. Installing a free **GitHub Actions Self-Hosted Runner** bridges GitHub to your local Docker stack securely over outbound HTTPS (no open firewall ports required).

### Step 1 — Set the deployment directory variable on GitHub

1. Open your repository on GitHub → **Settings** → **Secrets and variables** → **Actions** → **Variables** tab.
2. Click **New repository variable**:
   - **Name**: `MEDIFLOW_DEPLOY_DIR`
   - **Value**: `C:\Astik\Projects\MediFlow-agentic-health-management-platform` (your local repo path)

### Step 2 — Register the Self-Hosted Runner on Windows

1. Open your repository on GitHub → **Settings** → **Actions** → **Runners** → **New self-hosted runner**.
2. Select **Windows** (x64) and follow the download/extract commands shown by GitHub (e.g., into `C:\actions-runner`).
3. During `./config.cmd`:
   - When prompted for **additional labels**, enter:
     ```text
     mediflow-prod
     ```
   - When prompted to **run runner as a Windows service**, choose **Y** (so it starts automatically whenever Windows boots).

> **Note:** Make sure Docker Desktop is running when deployments trigger, and keep your local working tree clean on `main` so `git pull --ff-only origin main` succeeds cleanly.

### Step 3 — Verify

Push any commit to `main` (or trigger **MediFlow CD (Self-Hosted)** manually from the **Actions** tab). Once **MediFlow CI** passes, **MediFlow CD (Self-Hosted)** will automatically pull `main`, rebuild only the modified containers, and verify `http://localhost`.

---

## Manual One-Command Local Deploy (Anytime)

Even without the runner active, you can deploy local changes with one command from the repository root:

```powershell
# Smart deploy (rebuilds only containers affected by the latest commit)
powershell -ExecutionPolicy Bypass -File scripts/deploy.ps1

# Force rebuild all production containers
powershell -ExecutionPolicy Bypass -File scripts/deploy.ps1 -ForceAll
```
