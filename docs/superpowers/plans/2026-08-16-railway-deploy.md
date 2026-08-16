# Railway.app Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy Master Prediction as a single unified service on Railway.app (NiceGUI webapp + FastAPI API in one process), using Railway's $5/month free credit.

**Architecture:** One Docker container runs `webapp/main.py`, which starts NiceGUI on `$PORT`. The FastAPI API routers (`chat_router`, `perf_router`) are mounted directly on NiceGUI's internal FastAPI `app`, so both the UI and `/api/*` endpoints share the same process and port. Railway handles HTTPS, DNS, and auto-deploy from GitHub.

**Tech Stack:** Python 3.12, NiceGUI (WebSockets), FastAPI, Docker, Railway.app

## Global Constraints

- Existing Oracle Cloud files (`docker/`, `nginx/`, `scripts/`, `docker-compose.yml`) must NOT be modified or deleted.
- `requirements.txt` (original) must NOT be modified — it's used for local development.
- No ML libraries in `requirements-railway.txt` (no xgboost, catboost, lightgbm, scikit-learn).
- `PORT` env var is injected by Railway — never hardcode it.
- `reload=False` in production `ui.run()` to avoid file watcher.
- Data files (`team_features.parquet`, `national_*.json`) must be included in the Docker image via `COPY`.

---

### Task 1: Create `requirements-railway.txt`

**Files:**
- Create: `requirements-railway.txt`

**Interfaces:**
- Consumes: nothing
- Produces: `requirements-railway.txt` — used by `Dockerfile` in Task 2

- [ ] **Step 1: Create `requirements-railway.txt` with lightweight deps only**

```
# Web framework
nicegui>=3.15.0
fastapi>=0.115.0
uvicorn>=0.32.0

# Database
supabase>=2.10.0

# Data
pandas>=2.2.0
duckdb>=1.1.0
pyarrow>=18.0.0

# Auth
bcrypt>=4.0.0

# HTTP client
httpx>=0.28.0
requests>=2.32.0

# Utils
python-dotenv>=1.0.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
beautifulsoup4>=4.12.0
```

- [ ] **Step 2: Verify the file can be parsed by pip**

Run: `pip install --dry-run -r requirements-railway.txt 2>&1 | head -5`
Expected: No syntax errors. Output should show dependency resolution starting.

- [ ] **Step 3: Commit**

```bash
git add requirements-railway.txt
git commit -m "feat: add requirements-railway.txt with lightweight deps for Railway deploy"
```

---

### Task 2: Create root `Dockerfile` for Railway

**Files:**
- Create: `Dockerfile` (at repo root)

**Interfaces:**
- Consumes: `requirements-railway.txt` (from Task 1)
- Produces: `Dockerfile` — Railway autodetects this and uses it for builds

- [ ] **Step 1: Create `Dockerfile` at repo root**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt
COPY backend/ backend/
COPY webapp/ webapp/
COPY data/features/ data/features/
ENV PYTHONPATH=.
CMD ["python", "webapp/main.py"]
```

Note: This is separate from `docker/webapp.Dockerfile` (Oracle Cloud). Railway autodetects `Dockerfile` at repo root.

- [ ] **Step 2: Verify the Dockerfile builds locally**

Run: `docker build -t master-prediction-railway . 2>&1 | tail -10`
Expected: Build completes successfully. Last line should show the image tag.

If Docker is not available locally, skip this step — Railway will build it on push.

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: add root Dockerfile for Railway.app deployment"
```

---

### Task 3: Modify `webapp/main.py` — mount API routers + Railway PORT

**Files:**
- Modify: `webapp/main.py:1-10` (add import for API routers)
- Modify: `webapp/main.py:372-380` (modify `ui.run()` block)

**Interfaces:**
- Consumes: `backend.api.chat.router`, `backend.api.performance.router` (existing routers)
- Produces: Modified `webapp/main.py` — NiceGUI app that serves both UI and API on same port

- [ ] **Step 1: Add API router imports at top of file**

After the existing imports (after line 9 `from webapp.theme import CSS, SIDEBAR_ICONS, render_footer`), add:

```python
from backend.api.chat import router as chat_router
from backend.api.performance import router as perf_router
```

- [ ] **Step 2: Mount API routers on NiceGUI's app**

Before the `app.add_static_files(...)` line (line 371), add:

```python
app.include_router(chat_router)
app.include_router(perf_router)
```

- [ ] **Step 3: Modify `ui.run()` to read PORT and disable reload**

Replace the existing `ui.run(...)` block (lines 373-380) with:

```python
ui.run(
    title="Master Prediction",
    favicon="⚽",
    port=int(os.environ.get("PORT", 8080)),
    dark=True,
    storage_secret=os.environ.get("SUPABASE_KEY", "master-prediction-secret-key"),
    show=False,
    reload=False,
)
```

Changes: `port=8080` → `port=int(os.environ.get("PORT", 8080))`, added `reload=False`.

- [ ] **Step 4: Verify the app starts locally**

Run: `cd /Users/ivanmr/Documents/Documentos\ IMR/Personal\ IMR/IA/Golpredictor && PORT=8080 python webapp/main.py &`

Wait 5 seconds, then:
Run: `curl -s http://localhost:8080/login | head -5`
Expected: HTML response with NiceGUI content.

Run: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/chat -X POST -H "Content-Type: application/json" -H "X-API-Key: wrong" -d '{"message":"test"}'`
Expected: `401` (API key validation works — routers are mounted).

Kill the background process after testing.

- [ ] **Step 5: Commit**

```bash
git add webapp/main.py
git commit -m "feat: mount API routers on NiceGUI app and read PORT env var for Railway"
```

---

### Task 4: Un-gitignore `*.parquet` and commit data file

**Files:**
- Modify: `.gitignore` (line 16: change `*.parquet` rule)
- Track: `data/features/team_features.parquet` (6 MB, currently gitignored)

**Interfaces:**
- Consumes: nothing
- Produces: `team_features.parquet` committed to git — Docker `COPY data/features/` will include it in the image

- [ ] **Step 1: Add exception for `data/features/*.parquet` in `.gitignore`**

After line 16 (`*.parquet`), add an exception:

```
!data/features/*.parquet
```

This keeps the general `*.parquet` ignore but allows the specific files in `data/features/` to be tracked.

- [ ] **Step 2: Verify the parquet file is now visible to git**

Run: `git status data/features/team_features.parquet`
Expected: Shows as untracked file (no longer ignored).

- [ ] **Step 3: Commit the gitignore change and the parquet file**

```bash
git add .gitignore data/features/team_features.parquet
git commit -m "feat: track team_features.parquet for Railway Docker image (6 MB)"
```

- [ ] **Step 4: Verify the file is committed**

Run: `git log --oneline -1`
Expected: Shows the commit with the parquet file.

Run: `git show --stat HEAD`
Expected: Shows `.gitignore` and `data/features/team_features.parquet` in the commit.

---

### Task 5: Update `.dockerignore` and verify full build

**Files:**
- Modify: `.dockerignore` (ensure `data/features/` is NOT excluded)

**Interfaces:**
- Consumes: All files from Tasks 1-4
- Produces: Verified Docker build ready for Railway push

- [ ] **Step 1: Verify `.dockerignore` does not block `data/features/`**

Current `.dockerignore` has `data/raw/` and `data/processed/` excluded but NOT `data/features/`. Verify this is correct — no changes needed if `data/features/` is not listed.

If `data/features/` appears in `.dockerignore`, remove that line.

- [ ] **Step 2: Full Docker build test (if Docker available)**

Run: `docker build -t master-prediction-railway . 2>&1 | tail -15`
Expected: Build succeeds.

Run: `docker run --rm master-prediction-railway ls -lh /app/data/features/`
Expected: Shows `team_features.parquet` (6 MB), `national_h2h.json` (169 KB), `national_team_features.json` (21 KB).

If Docker is not available locally, skip — Railway will build on push.

- [ ] **Step 3: Commit if any `.dockerignore` changes were needed**

```bash
git add .dockerignore
git commit -m "fix: ensure data/features/ is included in Docker build"
```

Only commit if changes were made.

---

## Post-Implementation: Railway Setup (Manual)

These steps are done in the Railway dashboard after pushing code:

1. **Create project** at railway.app → New Project → Deploy from GitHub Repo
2. **Connect repo** `imolina29/master-prediction` → select `develop` branch (or `main`)
3. **Railway detects `Dockerfile`** and starts building automatically
4. **Set environment variables** in Settings → Variables:
   - `SUPABASE_URL` — same as local `.env`
   - `SUPABASE_KEY` — same as local `.env`
   - `FOOTBALL_DATA_TOKEN` — same as local `.env`
   - `API_KEY_WEBAPP` — same as local `.env`
   - `BACKEND_API_URL` — set to `http://localhost:${{PORT}}` (Railway variable reference)
5. **Generate domain** in Settings → Networking → Generate Domain
   - Railway assigns something like `master-prediction-production.up.railway.app`
6. **Verify** — open the Railway URL in browser, login page should appear
