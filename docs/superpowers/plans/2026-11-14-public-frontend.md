# Public Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public, SEO-friendly Next.js website that exposes Master Prediction's match predictions, team analytics, and track record to the internet, backed by new public API endpoints on the existing Python service.

**Architecture:** New FastAPI public router added to the existing NiceGUI app serves data from Supabase + parquet. A new Next.js 14 App Router service fetches from that API via Railway private networking, renders pages server-side with ISR (5-min revalidate), and serves them to the public. Both services deploy from the same monorepo on Railway.

**Tech Stack:** Python 3.12 / FastAPI / Supabase / DuckDB (backend); Next.js 14 / React 18 / Tailwind CSS 3 (frontend); Railway (deployment)

**Spec:** `docs/superpowers/specs/2026-11-14-public-frontend-design.md`

## Global Constraints

- All user-facing text in Spanish
- No new database — all data from existing Supabase tables and `data/features/team_features.parquet` via the Python API
- No breaking changes to existing NiceGUI dashboard, authenticated API endpoints, or ML pipeline
- Next.js 14 with App Router, Tailwind CSS, no UI component libraries
- ISR with `revalidate = 300`; no build-time static generation (`generateStaticParams` returns empty)
- If API is unreachable, pages show "Datos temporalmente no disponibles", not a 500
- Railway Hobby plan; no additional paid services
- Dark theme: background `#0a0a0a`, text white, accent `#d4a017`
- Inter font, `font-variant-numeric: tabular-nums` on numbers
- Disclaimer on every page: "Análisis informativo. Las decisiones de apuesta son responsabilidad exclusiva del usuario."

## Review Focus

1. **Accented team names in URLs**: A user navigates to `/partido/2026-11-21/atletico-madrid-vs-real-madrid` — the slug must match even though the DB stores "Atlético Madrid". Test: slug generation strips accents and normalizes.
2. **Empty upcoming predictions**: During international breaks, `/api/public/predictions/upcoming` returns `[]`. The home page and league pages must render gracefully with "No hay partidos programados". Test: API returns empty list, page renders without error.
3. **Division "EC" has no league_pos**: The match detail comparison table must omit the league position row for Champions League matches instead of showing 0 or null. Test: match detail for EC division omits `league_pos` row.
4. **Concurrent ISR revalidation while API is down**: The Next.js page must serve stale cached content and not throw. Test: fetch function returns null on network error, page component renders fallback.
5. **Rate limiter must not block internal Next.js requests**: The `X-Internal-Key` header must bypass the limiter. Test: request with valid key is not counted toward the rate limit.

---

### Task 1: Public API — Slug utilities and data access layer

**Files:**
- Create: `backend/api/public/__init__.py`
- Create: `backend/api/public/slugs.py`
- Create: `backend/api/public/data.py`
- Create: `tests/test_public_api_slugs.py`
- Create: `tests/test_public_api_data.py`

**Interfaces:**
- Consumes: `webapp.data.get_supabase_client`, `webapp.data.load_features`, `webapp.data.get_track_record`, `webapp.data.get_upcoming_predictions`
- Produces:
  - `slugify_team(name: str) -> str` — lowercase, strip accents, spaces to hyphens
  - `deslugify_team(slug: str, division: str | None) -> str | None` — reverse lookup from current features
  - `DIVISION_SLUGS: dict[str, str]` — `{"E0": "premier-league", ...}`
  - `SLUG_TO_DIVISION: dict[str, str]` — reverse
  - `DIVISION_DISPLAY: dict[str, str]` — `{"E0": "Premier League", ...}`
  - `get_team_features(team: str, division: str) -> dict | None` — latest features from parquet for one team
  - `get_match_elo(date: str, home: str, away: str) -> tuple[float, float] | None` — ELO pair from matches table
  - `get_accuracy_stats() -> dict` — overall, by confidence, by division accuracy from track record
  - `get_h2h(home: str, away: str, limit: int = 10) -> list[dict]` — head-to-head from matches table

- [ ] **Step 1: Write tests for `slugify_team` and `deslugify_team`**

```python
# tests/test_public_api_slugs.py
from backend.api.public.slugs import slugify_team, deslugify_team, DIVISION_SLUGS, SLUG_TO_DIVISION

def test_slugify_plain():
    assert slugify_team("Real Madrid") == "real-madrid"

def test_slugify_accents():
    assert slugify_team("Atlético Madrid") == "atletico-madrid"

def test_slugify_special():
    assert slugify_team("RC Deportivo La Coruña") == "rc-deportivo-la-coruna"

def test_division_slugs_complete():
    assert set(DIVISION_SLUGS.keys()) == {"E0", "SP1", "I1", "D1", "F1", "EC"}

def test_slug_to_division_roundtrip():
    for code, slug in DIVISION_SLUGS.items():
        assert SLUG_TO_DIVISION[slug] == code
```

- [ ] **Step 2: Run tests — expect FAIL (module not found)**

Run: `cd "/Users/ivanmr/Documents/Documentos IMR/Personal IMR/IA/Golpredictor" && python -m pytest tests/test_public_api_slugs.py -v`

- [ ] **Step 3: Implement `backend/api/public/slugs.py`**

`slugify_team`: use `unicodedata.normalize("NFD")` to decompose accents, filter combining marks, lowercase, replace spaces/underscores with hyphens, strip non-alphanumeric except hyphens. `deslugify_team`: build a reverse lookup dict from all team names in the features parquet on first call (cached). The six division mappings are plain dicts.

- [ ] **Step 4: Write tests for data access functions**

```python
# tests/test_public_api_data.py
from backend.api.public.data import get_team_features, get_accuracy_stats

def test_get_team_features_known():
    result = get_team_features("Real Madrid", "SP1")
    assert result is not None
    assert "goals_scored_avg" in result
    assert "xg_for_avg" in result
    assert isinstance(result["goals_scored_avg"], float)

def test_get_team_features_unknown():
    result = get_team_features("Nonexistent FC", "SP1")
    assert result is None

def test_get_accuracy_stats_shape():
    stats = get_accuracy_stats()
    assert "total" in stats
    assert "accuracy" in stats
    assert "by_confidence" in stats
    assert "by_division" in stats
    assert "alta" in stats["by_confidence"]
```

- [ ] **Step 5: Run tests — expect FAIL**

Run: `cd "/Users/ivanmr/Documents/Documentos IMR/Personal IMR/IA/Golpredictor" && python -m pytest tests/test_public_api_data.py -v`

- [ ] **Step 6: Implement `backend/api/public/data.py`**

`get_team_features`: filter `load_features()` for team+division+venue=="home", sort by match_date, take last row, return dict of the stat columns listed in the spec's data inventory. `get_match_elo`: query Supabase matches table by date+teams, return (home_elo, away_elo). `get_accuracy_stats`: call `get_track_record(limit=5000)`, compute overall accuracy, per-confidence accuracy, per-division accuracy, return structured dict. `get_h2h`: query matches table for both home/away orderings of the two teams, return list of dicts.

- [ ] **Step 7: Run all tests — expect PASS**

Run: `cd "/Users/ivanmr/Documents/Documentos IMR/Personal IMR/IA/Golpredictor" && python -m pytest tests/test_public_api_slugs.py tests/test_public_api_data.py -v`

- [ ] **Step 8: Commit**

```bash
git add backend/api/public/ tests/test_public_api_slugs.py tests/test_public_api_data.py
git commit -m "feat: add public API slug utilities and data access layer"
```

---

### Task 2: Public API — FastAPI router with rate limiting

**Files:**
- Create: `backend/api/public/router.py`
- Create: `tests/test_public_api_router.py`
- Modify: `webapp/main.py` (add `include_router` for public router)
- Modify: `requirements-railway.txt` (add `slowapi`)

**Interfaces:**
- Consumes: All functions from Task 1 (`slugify_team`, `deslugify_team`, `SLUG_TO_DIVISION`, `get_team_features`, `get_match_elo`, `get_accuracy_stats`, `get_h2h`), `webapp.data.get_upcoming_predictions`, `webapp.data.get_track_record`
- Produces:
  - `GET /api/public/health` → `{"status": "ok"}`
  - `GET /api/public/predictions/upcoming` → `{"predictions": [...]}`
  - `GET /api/public/predictions/track-record?page=1&per_page=50&division=SP1&confidence=alta` → `{"predictions": [...], "page": 1, "total": N}`
  - `GET /api/public/predictions/stats` → `{"total": N, "accuracy": 0.528, "by_confidence": {...}, "by_division": {...}}`
  - `GET /api/public/match/{date}/{home_slug}-vs-{away_slug}?division=SP1` → `{"prediction": {...}, "home_features": {...}, "away_features": {...}, "elo": {...}, "h2h": [...], "ventajas": {...}}`
  - `GET /api/public/league/{league_slug}/upcoming` → `{"league": {...}, "predictions": [...]}`
  - Rate limiter: 60/min per IP, bypassed by `X-Internal-Key` header matching `INTERNAL_API_KEY` env var

- [ ] **Step 1: Write tests for the router endpoints**

```python
# tests/test_public_api_router.py
import pytest
from fastapi.testclient import TestClient
from backend.api.public.router import router
from fastapi import FastAPI

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

def test_health(client):
    r = client.get("/api/public/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_upcoming(client):
    r = client.get("/api/public/predictions/upcoming")
    assert r.status_code == 200
    assert "predictions" in r.json()

def test_stats(client):
    r = client.get("/api/public/predictions/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "accuracy" in data
    assert "by_confidence" in data

def test_track_record_paginated(client):
    r = client.get("/api/public/predictions/track-record?page=1&per_page=10")
    assert r.status_code == 200
    data = r.json()
    assert "predictions" in data
    assert "page" in data

def test_league_upcoming(client):
    r = client.get("/api/public/league/la-liga/upcoming")
    assert r.status_code == 200
    data = r.json()
    assert "league" in data
    assert "predictions" in data

def test_league_invalid_slug(client):
    r = client.get("/api/public/league/invalid-league/upcoming")
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `cd "/Users/ivanmr/Documents/Documentos IMR/Personal IMR/IA/Golpredictor" && python -m pytest tests/test_public_api_router.py -v`

- [ ] **Step 3: Implement `backend/api/public/router.py`**

Create a FastAPI `APIRouter(prefix="/api/public")`. Add `slowapi` rate limiter: 60/min per IP, with an exemption callback that checks `request.headers.get("X-Internal-Key") == os.environ.get("INTERNAL_API_KEY")`. Each endpoint calls the data functions from Task 1. The match detail endpoint (`/match/{date}/{slug}`) parses the slug by splitting on `-vs-`, calls `deslugify_team` for both sides, queries predictions from Supabase for that date+teams, and assembles features+ELO+H2H. The `ventajas` field is built by comparing feature values: for each stat in `[goals_scored_avg, goals_conceded_avg, win_rate, xg_diff_avg, venue_win_rate, h2h_win_rate]`, generate a Spanish-language bullet when one team has a clear edge (>15% difference or >0.3 goal difference).

- [ ] **Step 4: Add `slowapi>=0.1.9` to `requirements-railway.txt`**

- [ ] **Step 5: Register the public router in `webapp/main.py`**

Add after the existing `app.include_router(perf_router)` line:

```python
from backend.api.public.router import router as public_router
app.include_router(public_router)
```

- [ ] **Step 6: Run all tests — expect PASS**

Run: `cd "/Users/ivanmr/Documents/Documentos IMR/Personal IMR/IA/Golpredictor" && python -m pytest tests/test_public_api_router.py tests/test_public_api_slugs.py tests/test_public_api_data.py -v`

- [ ] **Step 7: Manual smoke test — start the server and hit endpoints**

Run: `cd "/Users/ivanmr/Documents/Documentos IMR/Personal IMR/IA/Golpredictor" && python webapp/main.py &` then `curl http://localhost:8080/api/public/health` and `curl http://localhost:8080/api/public/predictions/stats`. Verify JSON responses.

- [ ] **Step 8: Commit**

```bash
git add backend/api/public/router.py tests/test_public_api_router.py webapp/main.py requirements-railway.txt
git commit -m "feat: add public API router with rate limiting and all endpoints"
```

---

### Task 3: Next.js scaffolding — project setup, layout, API client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tsconfig.json`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/constants.ts`
- Create: `frontend/Dockerfile`
- Create: `frontend/.gitignore`

**Interfaces:**
- Consumes: Public API endpoints from Task 2
- Produces:
  - `fetchAPI<T>(path: string): Promise<T | null>` — fetches from `API_BASE_URL` with `X-Internal-Key` header, returns null on error
  - Root layout with dark theme, Inter font, Tailwind, Spanish lang, meta defaults, disclaimer footer, GA4 slot (empty)
  - Type definitions: `Prediction`, `MatchDetail`, `TeamFeatures`, `AccuracyStats`, `LeagueInfo`
  - Constants: `DIVISIONS`, `CONFIDENCE_LABELS`, `CONFIDENCE_COLORS`

- [ ] **Step 1: Initialize the Next.js project**

Run `npx create-next-app@14 frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"` from the repo root. Then clean out the boilerplate (delete default page content, clean globals.css).

- [ ] **Step 2: Create `frontend/lib/types.ts`**

```typescript
export interface Prediction {
  match_date: string;
  home_team: string;
  away_team: string;
  division: string;
  predicted_result: "H" | "D" | "A";
  confidence: "alta" | "media" | "baja";
  prob_home: number;
  prob_draw: number;
  prob_away: number;
  prob_over25: number;
  prob_btts: number;
  ft_result?: "H" | "D" | "A" | null;
  ft_home_goals?: number | null;
  ft_away_goals?: number | null;
}

export interface TeamFeatures {
  goals_scored_avg: number;
  goals_conceded_avg: number;
  goals_scored_avg_3: number;
  goals_conceded_avg_3: number;
  xg_for_avg: number;
  xg_against_avg: number;
  win_rate: number;
  win_rate_3: number;
  btts_rate: number;
  over25_rate: number;
  venue_win_rate: number;
  venue_goals_avg: number;
  league_pos: number;
  h2h_win_rate: number;
  h2h_avg_goals: number;
  h2h_matches: number;
  xg_diff_avg: number;
}

export interface MatchDetail {
  prediction: Prediction;
  home_features: TeamFeatures | null;
  away_features: TeamFeatures | null;
  elo: { home: number; away: number } | null;
  h2h: Array<{ date: string; home_goals: number; away_goals: number; result: string }>;
  ventajas: { home: string[]; away: string[] };
}

export interface AccuracyStats {
  total: number;
  accuracy: number;
  by_confidence: Record<string, { total: number; correct: number; accuracy: number }>;
  by_division: Record<string, { total: number; correct: number; accuracy: number }>;
}

export interface LeagueInfo {
  code: string;
  slug: string;
  name: string;
  flag: string;
}
```

- [ ] **Step 3: Create `frontend/lib/constants.ts`**

```typescript
export const DIVISIONS: Record<string, { slug: string; name: string; flag: string }> = {
  E0:  { slug: "premier-league",   name: "Premier League",    flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
  SP1: { slug: "la-liga",          name: "La Liga",           flag: "🇪🇸" },
  I1:  { slug: "serie-a",         name: "Serie A",           flag: "🇮🇹" },
  D1:  { slug: "bundesliga",      name: "Bundesliga",        flag: "🇩🇪" },
  F1:  { slug: "ligue-1",         name: "Ligue 1",           flag: "🇫🇷" },
  EC:  { slug: "champions-league", name: "Champions League",  flag: "🏆" },
};

export const SLUG_TO_DIVISION: Record<string, string> = Object.fromEntries(
  Object.entries(DIVISIONS).map(([code, { slug }]) => [slug, code])
);

export const CONFIDENCE_COLORS: Record<string, string> = {
  alta: "#d4a017",
  media: "#6b7280",
  baja: "#4b5563",
};
```

- [ ] **Step 4: Create `frontend/lib/api.ts`**

```typescript
const API_BASE = process.env.API_BASE_URL || "http://localhost:8080";
const INTERNAL_KEY = process.env.INTERNAL_API_KEY || "";

export async function fetchAPI<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "X-Internal-Key": INTERNAL_KEY },
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
```

- [ ] **Step 5: Create root layout `frontend/app/layout.tsx`**

Root layout: `<html lang="es">`, dark background `#0a0a0a`, Inter font loaded via `next/font/google`, Tailwind globals, `<meta name="robots" content="index, follow">`, OG defaults. Body has a sticky header with "MP" logo linking to `/`, nav links (Ligas dropdown, Track Record, Acerca de), and a footer with disclaimer text and copyright. Reserved empty `<div id="ad-slot-footer">` for future ads. GA4 script slot: a `<Script>` tag that only renders when `NEXT_PUBLIC_GA_ID` env var is set.

- [ ] **Step 6: Configure `frontend/tailwind.config.js`**

Extend the default config with custom colors: `accent: "#d4a017"`, `surface: "#111111"`, `edge: "#1a1a1a"`, `bg: "#0a0a0a"`. Set `fontFamily.sans` to Inter. Add `tabular-nums` utility.

- [ ] **Step 7: Configure `frontend/next.config.js`**

Set `output: "standalone"` for Railway Docker deployment. No `generateStaticParams`. Set `images.unoptimized: true` (no external image optimizer needed).

- [ ] **Step 8: Create `frontend/Dockerfile`**

Use the exact Dockerfile from the spec: multi-stage node:20-alpine build, standalone output copy, expose 3000.

- [ ] **Step 9: Create `frontend/.gitignore`**

Standard Next.js gitignore: `.next/`, `node_modules/`, `out/`.

- [ ] **Step 10: Verify build**

Run: `cd frontend && npm install && npm run build`
Expected: Successful build with no errors.

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Next.js frontend with layout, API client, and types"
```

---

### Task 4: Home page

**Files:**
- Create: `frontend/app/page.tsx`
- Create: `frontend/components/match-card.tsx`
- Create: `frontend/components/confidence-badge.tsx`
- Create: `frontend/components/probability-bar.tsx`
- Create: `frontend/components/stats-grid.tsx`
- Create: `frontend/components/league-card.tsx`

**Interfaces:**
- Consumes: `fetchAPI` from Task 3, types `Prediction`, `AccuracyStats` from Task 3, `DIVISIONS` from Task 3
- Produces:
  - `MatchCard` component — reused on league page (Task 6)
  - `ConfidenceBadge` component — reused on match detail (Task 5)
  - `ProbabilityBar` component — reused on match detail (Task 5)
  - `StatsGrid` component — reused on track record page (Task 7)

- [ ] **Step 1: Create `frontend/components/confidence-badge.tsx`**

Server component. Props: `confidence: "alta" | "media" | "baja"`. Renders a small pill with the confidence label in Spanish, background color from `CONFIDENCE_COLORS`.

- [ ] **Step 2: Create `frontend/components/probability-bar.tsx`**

Server component. Props: `probHome: number, probDraw: number, probAway: number`. Renders three horizontal segments proportional to the three probabilities with percentage labels. Home=accent color, Draw=gray, Away=gray-lighter.

- [ ] **Step 3: Create `frontend/components/match-card.tsx`**

Server component. Props: `prediction: Prediction`. Renders a card with: league flag + name, match date formatted in Spanish (`new Intl.DateTimeFormat("es-ES", ...)`), home team vs away team, `ProbabilityBar`, predicted result highlighted, `ConfidenceBadge`. Card links to `/partido/{date}/{home-slug}-vs-{away-slug}`. Dark card with `border-edge` border.

- [ ] **Step 4: Create `frontend/components/stats-grid.tsx`**

Server component. Props: `stats: AccuracyStats`. Renders grid of stat cards: total predictions, overall accuracy %, alta/media/baja accuracy %. Numbers use `tabular-nums` and accent color.

- [ ] **Step 5: Create `frontend/components/league-card.tsx`**

Server component. Props: `code: string, slug: string, name: string, flag: string`. Renders a card linking to `/liga/{slug}` with flag and league name.

- [ ] **Step 6: Implement home page `frontend/app/page.tsx`**

Async server component. Fetches `/api/public/predictions/upcoming` and `/api/public/predictions/stats` via `fetchAPI`. If data is null, renders "Datos temporalmente no disponibles". Otherwise renders: hero section with headline "Predicciones de Fútbol Europeo" and stats summary, "Partidos Destacados" section with top 6 predictions sorted by confidence (alta first) as `MatchCard` grid, `StatsGrid` with accuracy, league cards grid linking to each league. JSON-LD structured data for the website (`WebSite` schema). `<title>` = "Master Prediction — Predicciones de Fútbol con IA". OG meta tags.

- [ ] **Step 7: Verify dev server**

Run: `cd frontend && npm run dev`, open `http://localhost:3000` in browser. Verify home page renders with real data from the Python API running on port 8080. Check mobile responsiveness.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/page.tsx frontend/components/
git commit -m "feat: implement home page with match cards and stats"
```

---

### Task 5: Match detail page

**Files:**
- Create: `frontend/app/partido/[date]/[slug]/page.tsx`
- Create: `frontend/components/team-comparison.tsx`
- Create: `frontend/components/ventajas.tsx`

**Interfaces:**
- Consumes: `fetchAPI` from Task 3, types `MatchDetail` from Task 3, `ConfidenceBadge` and `ProbabilityBar` from Task 4, `DIVISIONS` from Task 3
- Produces: Complete match detail page (terminal — no downstream consumers)

- [ ] **Step 1: Create `frontend/components/team-comparison.tsx`**

Server component. Props: `home: TeamFeatures | null, away: TeamFeatures | null, division: string, elo: {home: number, away: number} | null`. Renders a two-column comparison table. Rows: ELO rating, goals scored avg (season), goals scored avg (last 3), goals conceded avg (season), goals conceded avg (last 3), win rate (season), win rate (last 3), xG for avg, xG against avg, BTTS rate, Over 2.5 rate, league position (omitted when `division === "EC"`), H2H win rate, H2H avg goals. Each row highlights the better value in accent color. Skips rows where both values are null/undefined. On mobile, switches to a stacked vertical layout.

- [ ] **Step 2: Create `frontend/components/ventajas.tsx`**

Server component. Props: `ventajas: {home: string[], away: string[]}, homeTeam: string, awayTeam: string`. Renders two columns, each with 2-3 bullet points. Home advantages on left, away on right. Each bullet is a sentence in Spanish describing the statistical edge.

- [ ] **Step 3: Implement match detail page `frontend/app/partido/[date]/[slug]/page.tsx`**

Async server component. Extracts `date` and `slug` from params. Fetches `/api/public/match/{date}/{slug}` via `fetchAPI`. If null, renders fallback. Otherwise renders: teams header with league badge, date, predicted result + `ConfidenceBadge`, `ProbabilityBar`, `TeamComparison`, `Ventajas`, confidence explanation text (alta = "El modelo acierta el 82% de las predicciones con este nivel de confianza", media = "54%", baja = "36%"), disclaimer. `generateStaticParams` returns empty array. `generateMetadata` returns dynamic title like "Real Madrid vs Celta Vigo — Predicción | Master Prediction" and OG tags. JSON-LD `SportsEvent` structured data.

- [ ] **Step 4: Verify in browser**

Start Python backend + Next.js dev server. Navigate to a match detail page from the home page by clicking a match card. Verify all sections render, team comparison shows real data, mobile layout works.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/partido/ frontend/components/team-comparison.tsx frontend/components/ventajas.tsx
git commit -m "feat: implement match detail page with team comparison and ventajas"
```

---

### Task 6: League page

**Files:**
- Create: `frontend/app/liga/[slug]/page.tsx`

**Interfaces:**
- Consumes: `fetchAPI` from Task 3, `MatchCard` from Task 4, `SLUG_TO_DIVISION` and `DIVISIONS` from Task 3, types from Task 3
- Produces: Complete league page (terminal)

- [ ] **Step 1: Implement league page `frontend/app/liga/[slug]/page.tsx`**

Async server component. Extracts `slug` from params, maps to division code via `SLUG_TO_DIVISION`. If invalid slug, call `notFound()`. Fetches `/api/public/league/{slug}/upcoming` and `/api/public/predictions/stats` via `fetchAPI`. Renders: league header with flag + name, upcoming match cards grid using `MatchCard`, league-specific accuracy section (from stats `by_division`). If no upcoming matches, shows "No hay partidos programados para {league name} próximamente." `generateStaticParams` returns empty array. `generateMetadata` returns "Predicciones {league name} — Master Prediction".

- [ ] **Step 2: Verify in browser**

Navigate to `/liga/la-liga`. Verify matches appear, clicking a card navigates to match detail. Test `/liga/invalid-slug` returns 404 page.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/liga/
git commit -m "feat: implement league page with filtered predictions"
```

---

### Task 7: Track record page

**Files:**
- Create: `frontend/app/track-record/page.tsx`
- Create: `frontend/components/result-badge.tsx`

**Interfaces:**
- Consumes: `fetchAPI` from Task 3, `StatsGrid` from Task 4, `ConfidenceBadge` from Task 4, types from Task 3, `DIVISIONS` from Task 3
- Produces: Complete track record page (terminal)

- [ ] **Step 1: Create `frontend/components/result-badge.tsx`**

Server component. Props: `predicted: string, actual: string`. Renders a small badge: green check + "Acierto" when predicted === actual, red X + "Fallo" otherwise.

- [ ] **Step 2: Implement track record page `frontend/app/track-record/page.tsx`**

Async server component. Fetches `/api/public/predictions/stats` and `/api/public/predictions/track-record?page=1&per_page=50`. Renders: `StatsGrid` at top, league accuracy breakdown table (division name, total, correct, accuracy % — sorted by accuracy desc), recent results list with each row showing: date, teams, predicted result, actual result, `ResultBadge`, `ConfidenceBadge`. Client component wrapper for pagination and filtering (division select, confidence select) that re-fetches with query params. `generateMetadata` returns "Track Record — Master Prediction".

- [ ] **Step 3: Verify in browser**

Navigate to `/track-record`. Verify stats display, league breakdown table, and results list. Test filtering by league and confidence.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/track-record/ frontend/components/result-badge.tsx
git commit -m "feat: implement track record page with filtering"
```

---

### Task 8: Static pages, sitemap, SEO finalization

**Files:**
- Create: `frontend/app/about/page.tsx`
- Create: `frontend/app/disclaimer/page.tsx`
- Create: `frontend/app/sitemap.ts`
- Create: `frontend/app/robots.ts`
- Create: `frontend/app/not-found.tsx`

**Interfaces:**
- Consumes: `fetchAPI` from Task 3, `DIVISIONS` from Task 3
- Produces: Complete static pages, sitemap, robots.txt, 404 page (all terminal)

- [ ] **Step 1: Create about page `frontend/app/about/page.tsx`**

Static page. Spanish copy explaining: Master Prediction is a sports analytics platform using machine learning (XGBoost) trained on 100,000+ historical matches across 5 European leagues + Champions League. Describes what users get: predictions with probabilities, team statistics, transparent track record. Single-person project. No mention of betting — focus on "análisis deportivo con inteligencia artificial". `generateMetadata` returns "Acerca de — Master Prediction".

- [ ] **Step 2: Create disclaimer page `frontend/app/disclaimer/page.tsx`**

Static page. Spanish legal disclaimer: all analysis is informational only, not financial or betting advice, past performance does not guarantee future results, users assume all risk for their decisions, Master Prediction is not affiliated with any betting house or sports organization. `generateMetadata` returns "Aviso Legal — Master Prediction".

- [ ] **Step 3: Create sitemap `frontend/app/sitemap.ts`**

Dynamic sitemap function. Fetches `/api/public/predictions/upcoming` to get current matches. Returns entries for: `/` (daily), each `/liga/{slug}` (daily), each `/partido/{date}/{slug}` (weekly), `/track-record` (daily), `/about` (monthly), `/disclaimer` (monthly).

- [ ] **Step 4: Create robots.txt `frontend/app/robots.ts`**

Allow all crawlers. Point to sitemap at `{SITE_URL}/sitemap.xml`.

- [ ] **Step 5: Create 404 page `frontend/app/not-found.tsx`**

"Página no encontrada" message with link back to home.

- [ ] **Step 6: Verify sitemap and robots**

Run dev server. Check `http://localhost:3000/sitemap.xml` returns valid XML with match URLs. Check `http://localhost:3000/robots.txt` is correct.

- [ ] **Step 7: Commit**

```bash
git add frontend/app/about/ frontend/app/disclaimer/ frontend/app/sitemap.ts frontend/app/robots.ts frontend/app/not-found.tsx
git commit -m "feat: add about, disclaimer, sitemap, robots.txt, and 404 page"
```

---

### Task 9: Deployment configuration

**Files:**
- Modify: `frontend/Dockerfile` (verify it builds successfully)
- Create: `frontend/.env.example`

**Interfaces:**
- Consumes: Everything from Tasks 1–8
- Produces: Deployable configuration for Railway (terminal)

- [ ] **Step 1: Create `frontend/.env.example`**

```
API_BASE_URL=http://master-prediction-api.railway.internal:8080
INTERNAL_API_KEY=your-shared-secret-here
NEXT_PUBLIC_SITE_URL=https://www.masterprediction.com
NEXT_PUBLIC_GA_ID=
```

- [ ] **Step 2: Verify Docker build**

Run from repo root: `cd frontend && docker build -t mp-frontend .`
Expected: Successful build producing a working image.

- [ ] **Step 3: Verify Docker run**

Run: `docker run -p 3000:3000 -e API_BASE_URL=http://host.docker.internal:8080 mp-frontend`
Navigate to `http://localhost:3000` and verify pages load.

- [ ] **Step 4: Add `INTERNAL_API_KEY` env var to Python service**

Add to `.env`: `INTERNAL_API_KEY=` with a generated secret. The public router (Task 2) already reads this for rate limit exemption.

- [ ] **Step 5: Full integration test**

Start Python backend on 8080, Next.js on 3000. Navigate through: Home → click match card → match detail → back → click league → league page → track record → about → disclaimer. Verify all pages render, no errors in console, mobile responsive.

- [ ] **Step 6: Commit**

```bash
git add frontend/.env.example frontend/Dockerfile
git commit -m "feat: add deployment configuration and env example"
```
