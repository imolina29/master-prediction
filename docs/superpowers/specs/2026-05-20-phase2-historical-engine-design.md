# Phase 2: Historical Engine — Design Spec

## Goal

Enrich the existing 100K match dataset with xG data from Understat, generate derived features for ML, and build a 3-page Streamlit dashboard for historical analysis.

## Architecture

Three independent subsystems built in sequence:

```
Supabase (matches: 100K rows)
        │
        ├──► Understat Scraper ──► Supabase (match_xg: ~20K rows)
        │
        ├──► Feature Engine ──► data/features/team_features.parquet
        │                              │
        │                              ▼
        └──────────────────► Streamlit Dashboard (3 pages)
                              reads from Supabase + Parquet via DuckDB
```

## Subsystem 1: Understat Scraper

### Data Source

Understat embeds match-level xG data as JSON inside `<script>` tags in league pages. No API — HTML parsing required.

- URL pattern: `https://understat.com/league/{league}/{year}`
- Coverage: Top 5 leagues, 2014/15 → 2024/25
- Data per match: home_xg, away_xg, home_goals, away_goals, date, teams

### League Mapping

| Understat slug | Our division code |
|---------------|-------------------|
| EPL | E0 |
| La_Liga | SP1 |
| Bundesliga | D1 |
| Serie_A | I1 |
| Ligue_1 | F1 |

### Pipeline Flow

```
For each league in [EPL, La_Liga, Bundesliga, Serie_A, Ligue_1]:
  For each season in [2014..2024]:
    1. GET https://understat.com/league/{league}/{season}
    2. Extract JSON from <script> tag (regex: datesData)
    3. Parse match list: date, home/away team, home/away xG, home/away goals
    4. Normalize team names via TeamNormalizer
    5. Map league slug → division code
    6. Upsert to match_xg table
    7. Sleep 1.5s between requests
```

### Rate Limiting

- 1.5 second delay between requests
- ~55 total requests (5 leagues × 11 seasons)
- Total scraping time: ~90 seconds

### New Database Table

```sql
CREATE TABLE IF NOT EXISTS match_xg (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    division TEXT NOT NULL,
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_xg REAL NOT NULL,
    away_xg REAL NOT NULL,
    home_goals SMALLINT,
    away_goals SMALLINT,
    source TEXT NOT NULL DEFAULT 'understat',
    UNIQUE(division, match_date, home_team, away_team)
);

CREATE INDEX IF NOT EXISTS idx_match_xg_date ON match_xg(match_date);
CREATE INDEX IF NOT EXISTS idx_match_xg_division ON match_xg(division);
```

### Team Name Reconciliation

Understat uses different team names than our canonical names. Examples:
- "Manchester United" (Understat) vs "Manchester United" (ours) — same
- "Wolverhampton Wanderers" (Understat) vs "Wolverhampton" (ours) — needs alias

Extend `data/team_mappings.json` with Understat-specific aliases. Run a reconciliation script after first scrape to identify unmapped names.

### Files

```
backend/etl/understat.py       # Scraper: fetch, parse, normalize
tests/test_understat.py        # Tests with mocked HTML responses
scripts/run_understat.py       # Runner script
```

---

## Subsystem 2: Feature Engine

### Purpose

Generate derived features from raw match data + xG data. These features serve two consumers:
1. **Dashboard** (Phase 2) — for visualizations and tables
2. **ML models** (Phase 3) — as training features

### Input

- `matches` table from Supabase (100K rows)
- `match_xg` table from Supabase (~20K rows)

### Output

- `data/features/team_features.parquet` — one row per team per match, with rolling features computed from prior matches only (no data leakage)

### Feature Definitions

All rolling features use a lookback window of the team's N most recent matches BEFORE the current match date. Home/away splits use only home or away matches respectively.

| Feature | Window | Type | Description |
|---------|--------|------|-------------|
| goals_scored_avg_5 | 5 | float | Mean goals scored |
| goals_conceded_avg_5 | 5 | float | Mean goals conceded |
| goals_scored_avg_10 | 10 | float | Mean goals scored |
| goals_conceded_avg_10 | 10 | float | Mean goals conceded |
| xg_for_avg_5 | 5 | float | Mean xG created |
| xg_against_avg_5 | 5 | float | Mean xG conceded |
| xg_diff_avg_5 | 5 | float | Mean xG differential |
| shots_target_avg_5 | 5 | float | Mean shots on target |
| corners_avg_5 | 5 | float | Mean corners |
| win_rate_5 | 5 | float | Win percentage (0-1) |
| draw_rate_5 | 5 | float | Draw percentage (0-1) |
| btts_rate_5 | 5 | float | Both teams scored % |
| over25_rate_5 | 5 | float | Over 2.5 goals % |
| home_win_rate_5 | 5 home | float | Home win % (home matches only) |
| away_win_rate_5 | 5 away | float | Away win % (away matches only) |
| xg_overperformance | 10 | float | Actual goals minus xG (luck indicator) |
| h2h_wins | all | int | Total H2H wins vs opponent |
| h2h_draws | all | int | Total H2H draws vs opponent |
| h2h_goals_avg | last 5 H2H | float | Mean total goals in H2H matches |

### Data Leakage Prevention

Features for match on date D use ONLY data from matches BEFORE date D. This is enforced by sorting by date and using `shift()` / expanding windows that exclude the current row.

### Processing

1. Read all matches from Supabase into pandas DataFrame
2. Left-join with match_xg on (division, match_date, home_team, away_team)
3. Sort by date
4. For each team: compute rolling features using only prior matches
5. Save as Parquet to `data/features/team_features.parquet`

### Files

```
backend/services/features.py   # Feature computation logic
tests/test_features.py         # Tests with sample data
scripts/run_features.py        # Runner script
```

---

## Subsystem 3: Streamlit Dashboard

### Data Access

Dashboard reads from:
- Parquet files via DuckDB for feature data (fast, no Supabase hits)
- Supabase directly for raw match data (via supabase-py client)

### Pages

#### Page 1: League Overview (`dashboard/pages/1_league_overview.py`)

- **Controls**: league selector (dropdown), season selector (dropdown)
- **Main content**: enriched standings table with columns:
  - Position, Team, P, W, D, L, GF, GA, GD, Pts
  - xG, xGA, xGD (from match_xg)
  - Form (last 5 results as colored W/D/L indicators)
  - O/U 2.5 rate, BTTS rate
- Table is sorteable by clicking column headers
- Color coding: green for positive xGD, red for negative

#### Page 2: Team Analysis (`dashboard/pages/2_team_analysis.py`)

- **Controls**: team selector (dropdown, searchable), season selector
- **Metrics row**: P, W, D, L, GF, GA, xG, xGA
- **Chart 1**: Line chart — xG vs actual goals per matchday (Plotly)
- **Chart 2**: Bar chart — home vs away results breakdown
- **Table**: last 10 match results with opponent, score, xG

#### Page 3: Match Comparator (`dashboard/pages/3_match_comparator.py`)

- **Controls**: two team selectors (dropdowns)
- **Side-by-side stats**: goals avg, xG avg, form, home/away record
- **H2H table**: all historical encounters between the two teams
- **Radar chart**: comparing 6 dimensions (goals, xG, defense, shots, corners, discipline)

### Deployment

Streamlit Community Cloud (free) connected to the GitHub repo. The app reads from Parquet files committed to the repo (feature data) and Supabase (raw data + xG).

### Files

```
dashboard/
├── app.py                              # Main entry point
├── pages/
│   ├── 1_league_overview.py
│   ├── 2_team_analysis.py
│   └── 3_match_comparator.py
├── components/
│   ├── charts.py                       # Plotly chart builders
│   └── tables.py                       # Table formatters
└── data_access.py                      # DuckDB + Supabase queries
```

---

## Updated ETL Pipeline

The existing GitHub Actions ETL cron (daily at 6AM UTC) will be extended:

```
1. Download + load matches (existing)
2. Scrape Understat for current season xG (new)
3. Regenerate features Parquet (new)
4. Commit updated Parquet to repo (new — so Streamlit Cloud can access it)
```

Step 4 requires the GitHub Actions workflow to commit and push the updated Parquet file. This is a common pattern for data pipelines.

---

## Team Mappings Extension

New Understat aliases will be added to `data/team_mappings.json`. After the first scrape, a reconciliation script identifies any Understat team names that don't match our canonical names, so we can add missing aliases.

### Files

```
scripts/reconcile_teams.py     # Find unmapped team names
```

---

## Scope Exclusions (NOT in Phase 2)

- StatsBomb Open Data ingestion (deferred — Understat covers xG needs)
- FBref scraping (deferred to Phase 3 or later)
- Player-level statistics (team-level only for now)
- Real-time or live data
- Any ML models or predictions (Phase 3)
