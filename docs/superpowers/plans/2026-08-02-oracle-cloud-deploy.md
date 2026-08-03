# Oracle Cloud Always Free Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create all Docker, nginx, and deploy files needed to run Master Prediction on an Oracle Cloud Always Free ARM VM with $0/month cost.

**Architecture:** Four Docker Compose services (webapp, api, nginx, certbot) behind nginx reverse proxy with SSL. NiceGUI webapp on port 8080 requires WebSocket proxy headers. FastAPI API on port 8081. DuckDNS for free domain, Let's Encrypt for SSL. Data parquet file mounted as shared volume between host and webapp container.

**Tech Stack:** Docker, Docker Compose, nginx, certbot, DuckDNS, Ubuntu 22.04 ARM

## Global Constraints

- All Docker images use `python:3.12-slim` base (ARM-compatible)
- The API entry point is `backend.api.app:app` (not `backend.api.main:app`)
- `PYTHONPATH=.` is required for both webapp and api containers
- NiceGUI requires WebSocket upgrade headers in nginx (`Upgrade`, `Connection`, `proxy_http_version 1.1`)
- `requirements.txt` must include `nicegui>=3.15.0` — currently missing
- `data/features/team_features.parquet` (6MB) is gitignored — must be volume-mounted from host into webapp container
- The `docs/` directory is in `.gitignore` — all Docker/nginx/deploy files go in `docker/`, `nginx/`, and `scripts/`
- The editable install line (`-e .`) in `requirements.txt` does not work in Docker — must be removed or replaced for the Docker build
- `BACKEND_API_URL` defaults to `http://localhost:8081` in webapp code — must be set to `http://api:8081` in Docker `.env`

---

### Task 1: Fix requirements.txt for Docker compatibility

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: nothing
- Produces: A `requirements.txt` that installs cleanly in Docker (no `-e .`) and includes NiceGUI

- [ ] **Step 1: Add NiceGUI and remove editable install**

Open `requirements.txt` and make these changes:

1. Add under the `# Dashboard` section:
```
nicegui>=3.15.0
```

2. Replace the last line:
```
# REMOVE this line:
-e .

# REPLACE with:
# Local packages (installed as regular package in Docker)
```

The final `requirements.txt` should end with:
```
# Dev
pytest>=8.3.0
ruff>=0.8.0
```

No `-e .` line — the Docker COPY already puts code in `/app`, so no editable install is needed.

- [ ] **Step 2: Verify requirements parse correctly**

Run:
```bash
pip install --dry-run -r requirements.txt 2>&1 | tail -5
```

Expected: No parse errors. Some packages may say "already installed".

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "fix: add nicegui to requirements.txt, remove editable install for Docker"
```

---

### Task 2: Create Docker files for webapp and api

**Files:**
- Create: `docker/webapp.Dockerfile`
- Create: `docker/api.Dockerfile`
- Create: `.dockerignore`

**Interfaces:**
- Consumes: `requirements.txt` (from Task 1)
- Produces: Two Dockerfiles that build the webapp and api containers

- [ ] **Step 1: Create docker directory**

```bash
mkdir -p docker
```

- [ ] **Step 2: Create webapp Dockerfile**

Create `docker/webapp.Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY webapp/ webapp/

ENV PYTHONPATH=.

EXPOSE 8080

CMD ["python", "webapp/main.py"]
```

Note: We copy only `backend/` and `webapp/` (not the whole repo) because the webapp imports from both `webapp.*` and `backend.*` (e.g., `webapp.data` imports `supabase`, and `webapp/pages/asesor.py` calls the API). The `data/features/` parquet is mounted as a volume at runtime.

- [ ] **Step 3: Create api Dockerfile**

Create `docker/api.Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/

ENV PYTHONPATH=.

EXPOSE 8081

CMD ["uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8081"]
```

- [ ] **Step 4: Create .dockerignore**

Create `.dockerignore` at repo root:

```
.venv/
.git/
.github/
__pycache__/
*.pyc
.env
.env.*
*.log
.DS_Store
.nicegui/
models/
data/raw/
data/processed/
.streamlit/
docs/
tests/
.claude/
.ruff_cache/
```

- [ ] **Step 5: Verify Dockerfiles have valid syntax**

```bash
docker build --check -f docker/webapp.Dockerfile . 2>&1 || echo "check flag not supported, syntax looks ok"
```

(The `--check` flag may not exist in all Docker versions — visual inspection is fine.)

- [ ] **Step 6: Commit**

```bash
git add docker/webapp.Dockerfile docker/api.Dockerfile .dockerignore
git commit -m "feat: add Dockerfiles for webapp and api containers"
```

---

### Task 3: Create nginx configuration

**Files:**
- Create: `nginx/nginx.conf`

**Interfaces:**
- Consumes: nothing
- Produces: nginx config that proxies to webapp (with WebSocket) and api, handles SSL, and serves certbot challenges

- [ ] **Step 1: Create nginx directory**

```bash
mkdir -p nginx
```

- [ ] **Step 2: Create nginx.conf**

Create `nginx/nginx.conf`:

```nginx
# HTTP — certbot challenges + redirect to HTTPS
server {
    listen 80;
    server_name masterprediction.duckdns.org;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS — reverse proxy to webapp and api
server {
    listen 443 ssl;
    server_name masterprediction.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/masterprediction.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/masterprediction.duckdns.org/privkey.pem;

    # API backend
    location /api/ {
        proxy_pass http://api:8081/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # NiceGUI webapp (requires WebSocket upgrade)
    location / {
        proxy_pass http://webapp:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

The `proxy_read_timeout 86400` prevents nginx from closing idle WebSocket connections after 60 seconds (the default).

- [ ] **Step 3: Commit**

```bash
git add nginx/nginx.conf
git commit -m "feat: add nginx reverse proxy config with WebSocket support"
```

---

### Task 4: Create docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

**Interfaces:**
- Consumes: `docker/webapp.Dockerfile`, `docker/api.Dockerfile`, `nginx/nginx.conf` (from Tasks 2-3)
- Produces: `docker-compose.yml` that orchestrates all 4 services

- [ ] **Step 1: Create docker-compose.yml**

Create `docker-compose.yml` at repo root:

```yaml
services:
  webapp:
    build:
      context: .
      dockerfile: docker/webapp.Dockerfile
    env_file: .env
    volumes:
      - ./data/features:/app/data/features:ro
      - ./webapp/static:/app/webapp/static:ro
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    env_file: .env
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - certbot-etc:/etc/letsencrypt
      - certbot-www:/var/www/certbot
    depends_on:
      - webapp
      - api
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-www:/var/www/certbot

volumes:
  certbot-etc:
  certbot-www:
```

Key details:
- `./data/features:/app/data/features:ro` mounts the parquet file from the host (since it's gitignored and must be generated on the VM)
- `./webapp/static:/app/webapp/static:ro` mounts static assets so you can update banners without rebuilding
- No `version:` key — deprecated in Docker Compose v2+
- certbot has no `restart` — it runs on-demand, not as a daemon

- [ ] **Step 2: Validate compose file syntax**

```bash
docker compose config --quiet 2>&1 && echo "VALID" || echo "INVALID"
```

Expected: `VALID` (or warnings about missing `.env`, which is fine)

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose.yml with 4 services (webapp, api, nginx, certbot)"
```

---

### Task 5: Create deploy script and VM setup guide

**Files:**
- Create: `scripts/deploy.sh`
- Create: `scripts/vm-setup.sh`

**Interfaces:**
- Consumes: `docker-compose.yml` (from Task 4)
- Produces: One-command deploy script and a VM bootstrap script

- [ ] **Step 1: Create deploy script**

Create `scripts/deploy.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Deploy Master Prediction to the Oracle Cloud VM.
# Usage: ./scripts/deploy.sh [ssh-host]
# Example: ./scripts/deploy.sh ubuntu@129.153.x.x

HOST="${1:-mp-vm}"
REMOTE_DIR="master-prediction"

echo "Deploying to $HOST..."
ssh "$HOST" "cd $REMOTE_DIR && git pull && docker compose up -d --build"
echo "Deploy complete. Check: https://masterprediction.duckdns.org"
```

- [ ] **Step 2: Create VM setup script**

Create `scripts/vm-setup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# One-time setup for Oracle Cloud ARM VM (Ubuntu 22.04).
# Run this via SSH on the VM after first boot.

echo "=== Updating system ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== Installing Docker ==="
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== Adding user to docker group ==="
sudo usermod -aG docker "$USER"

echo "=== Opening firewall ports ==="
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Log out and back in (for docker group)"
echo "  2. Clone repo: git clone git@github.com:imolina29/master-prediction.git"
echo "  3. Copy .env to master-prediction/.env"
echo "  4. Generate features parquet: cd master-prediction && python scripts/run_features.py"
echo "  5. Start: cd master-prediction && docker compose up -d --build"
echo "  6. Get SSL cert: docker compose run certbot certonly --webroot -w /var/www/certbot -d masterprediction.duckdns.org"
echo "  7. Restart nginx: docker compose restart nginx"
```

- [ ] **Step 3: Make scripts executable**

```bash
chmod +x scripts/deploy.sh scripts/vm-setup.sh
```

- [ ] **Step 4: Commit**

```bash
git add scripts/deploy.sh scripts/vm-setup.sh
git commit -m "feat: add deploy script and VM setup script for Oracle Cloud"
```

---

### Task 6: Create DuckDNS and SSL renewal cron scripts

**Files:**
- Create: `scripts/duckdns-update.sh`
- Create: `scripts/renew-ssl.sh`

**Interfaces:**
- Consumes: nothing
- Produces: Cron-ready scripts for DuckDNS IP updates and SSL renewal

- [ ] **Step 1: Create DuckDNS update script**

Create `scripts/duckdns-update.sh`:

```bash
#!/usr/bin/env bash
# DuckDNS IP update — run via cron every 5 minutes:
#   */5 * * * * /home/ubuntu/master-prediction/scripts/duckdns-update.sh >> /var/log/duckdns.log 2>&1

DUCKDNS_TOKEN="${DUCKDNS_TOKEN:-}"
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN:-masterprediction}"

if [ -z "$DUCKDNS_TOKEN" ]; then
    echo "$(date): DUCKDNS_TOKEN not set"
    exit 1
fi

curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&verbose=true"
echo ""
```

- [ ] **Step 2: Create SSL renewal script**

Create `scripts/renew-ssl.sh`:

```bash
#!/usr/bin/env bash
# SSL certificate renewal — run via cron every 2 months:
#   0 3 1 */2 * /home/ubuntu/master-prediction/scripts/renew-ssl.sh >> /var/log/ssl-renew.log 2>&1

set -euo pipefail

PROJECT_DIR="${1:-/home/ubuntu/master-prediction}"

cd "$PROJECT_DIR"
docker compose run --rm certbot renew
docker compose restart nginx

echo "$(date): SSL renewal complete"
```

- [ ] **Step 3: Make scripts executable**

```bash
chmod +x scripts/duckdns-update.sh scripts/renew-ssl.sh
```

- [ ] **Step 4: Commit**

```bash
git add scripts/duckdns-update.sh scripts/renew-ssl.sh
git commit -m "feat: add DuckDNS update and SSL renewal cron scripts"
```

---

### Task 7: Local Docker build and smoke test

**Files:**
- No new files — validation only

**Interfaces:**
- Consumes: All files from Tasks 1-6
- Produces: Confidence that images build and containers start

- [ ] **Step 1: Build Docker images locally**

```bash
docker compose build webapp api
```

Expected: Both images build successfully. Watch for pip install errors (missing packages, architecture issues on ARM if testing on x86 — that's OK, the VM is ARM).

- [ ] **Step 2: Test webapp container starts**

```bash
docker compose up webapp -d
sleep 3
docker compose logs webapp 2>&1 | tail -10
```

Expected: NiceGUI startup message showing port 8080. If it fails with import errors, check `requirements.txt`.

- [ ] **Step 3: Test api container starts**

```bash
docker compose up api -d
sleep 3
docker compose logs api 2>&1 | tail -10
```

Expected: Uvicorn startup message showing port 8081.

- [ ] **Step 4: Stop containers and clean up**

```bash
docker compose down
```

- [ ] **Step 5: Final commit with any fixes**

If any fixes were needed during smoke testing:

```bash
git add -A
git commit -m "fix: resolve Docker build issues found during smoke test"
```

If no fixes needed, skip this step.

---

## Post-Plan: Manual Steps on Oracle Cloud

These steps happen on the Oracle Cloud console and VM — not automatable in the repo:

1. **Oracle Cloud Console:**
   - Create Always Free ARM VM (2 OCPU, 12GB RAM, Ubuntu 22.04)
   - Assign static public IP
   - Add Security List rules for ports 80, 443, 22

2. **DuckDNS:**
   - Register at duckdns.org
   - Create subdomain `masterprediction` pointing to VM's public IP

3. **On the VM via SSH:**
   - Run `scripts/vm-setup.sh`
   - Log out and back in
   - Clone repo, copy `.env`, generate features parquet
   - `docker compose up -d --build`
   - Get first SSL cert: `docker compose run certbot certonly --webroot -w /var/www/certbot -d masterprediction.duckdns.org`
   - `docker compose restart nginx`
   - Add cron jobs:
     ```
     crontab -e
     # Add these lines:
     */5 * * * * DUCKDNS_TOKEN=your_token /home/ubuntu/master-prediction/scripts/duckdns-update.sh >> /var/log/duckdns.log 2>&1
     0 3 1 */2 * /home/ubuntu/master-prediction/scripts/renew-ssl.sh >> /var/log/ssl-renew.log 2>&1
     ```

4. **Verify:** Open `https://masterprediction.duckdns.org` in a browser — should show the login page.
