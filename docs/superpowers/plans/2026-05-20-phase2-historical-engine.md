# Phase 2 — Historical Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich 100K matches with xG from Understat, generate rolling features, and build a 3-page Streamlit dashboard for historical analysis.

**Architecture:** Understat JSON API → Supabase `match_xg` table → Feature Engine (pandas) → Parquet file → Streamlit dashboard reads from Parquet (DuckDB) + Supabase.

**Tech Stack:** Python 3.13, httpx, pandas, DuckDB, Parquet (pyarrow), Streamlit, Plotly, Supabase

---

## File Structure

```
backend/
├── etl/
│   └── understat.py             # Fetch + parse Understat JSON API
├── services/
│   └── features.py              # Rolling feature computation
dashboard/
├── app.py                       # Streamlit main entry
├── data_access.py               # DuckDB + Supabase query layer
├── pages/
│   ├── 1_league_overview.py     # Enriched standings
│   ├── 2_team_analysis.py       # Single team deep dive
│   └── 3_match_comparator.py    # H2H comparison
└── components/
    ├── charts.py                # Plotly chart builders
    └── tables.py                # Table formatting helpers
tests/
├── test_understat.py
└── test_features.py
scripts/
├── run_understat.py             # Understat scraper runner
├── run_features.py              # Feature generation runner
└── reconcile_teams.py           # Find unmapped Understat team names
data/
├── team_mappings.json           # Extended with Understat aliases
└── features/
    └── team_features.parquet    # Generated features (gitignored)
backend/db/
└── schema_xg.sql               # match_xg table DDL
```

---

## Task 1: match_xg Schema + Understat Team Mappings

**Files:**
- Create: `backend/db/schema_xg.sql`
- Modify: `data/team_mappings.json`

- [ ] **Step 1: Create schema_xg.sql**

```sql
-- backend/db/schema_xg.sql

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

- [ ] **Step 2: Run schema_xg.sql in Supabase SQL Editor**

Go to Supabase Dashboard → SQL Editor → paste the SQL above → Run. Verify `match_xg` table exists.

- [ ] **Step 3: Add Understat team aliases to team_mappings.json**

Add these entries to the `"aliases"` object in `data/team_mappings.json`:

```json
"Wolverhampton Wanderers": "Wolverhampton",
"Newcastle United": "Newcastle",
"Nottingham Forest": "Nottingham Forest",
"Leicester": "Leicester",
"Ipswich": "Ipswich",
"Southampton": "Southampton",
"West Ham": "West Ham",
"Crystal Palace": "Crystal Palace",
"Brighton": "Brighton",
"Brentford": "Brentford",
"Bournemouth": "Bournemouth",
"Everton": "Everton",
"Fulham": "Fulham",
"Real Sociedad": "Real Sociedad",
"Atletico Madrid": "Atletico Madrid",
"Athletic Club": "Athletic Bilbao",
"Celta Vigo": "Celta Vigo",
"Deportivo Alaves": "Deportivo Alaves",
"Rayo Vallecano": "Rayo Vallecano",
"RasenBallsport Leipzig": "RB Leipzig",
"Eintracht Frankfurt": "Ein Frankfurt",
"Borussia Dortmund": "Borussia Dortmund",
"Borussia M.Gladbach": "Borussia Monchengladbach",
"Bayern Munich": "Bayern Munich",
"VfL Wolfsburg": "Wolfsburg",
"VfB Stuttgart": "Stuttgart",
"SC Freiburg": "Freiburg",
"TSG Hoffenheim": "Hoffenheim",
"FC Koln": "Koln",
"Hellas Verona": "Verona",
"Internazionale": "Inter Milan",
"AC Milan": "AC Milan",
"Paris Saint Germain": "Paris SG",
"Olympique Marseille": "Marseille",
"Olympique Lyonnais": "Lyon",
"AS Monaco": "Monaco",
"Stade Rennais": "Rennes"
```

Also add any missing entries to `"canonical_metadata"` for new teams.

Note: Some of these names may already exist or may not be needed. The reconciliation script (Task 3) will identify exact gaps after the first real scrape.

- [ ] **Step 4: Commit**

```bash
git add backend/db/schema_xg.sql data/team_mappings.json
git commit -m "feat: add match_xg schema and Understat team aliases"
```

---

## Task 2: Understat Scraper

**Files:**
- Create: `backend/etl/understat.py`
- Create: `tests/test_understat.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_understat.py
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.etl.understat import (
    LEAGUE_MAP,
    fetch_league_season,
    parse_matches,
    scrape_all,
)

SAMPLE_API_RESPONSE = {
    "dates": [
        {
            "id": "1001",
            "isResult": True,
            "h": {"id": "1", "title": "Arsenal", "short_title": "ARS"},
            "a": {"id": "2", "title": "Manchester City", "short_title": "MCI"},
            "goals": {"h": "2", "a": "1"},
            "xG": {"h": "1.85", "a": "1.23"},
            "datetime": "2024-08-17 15:00:00",
            "forecast": {"w": "0.5", "d": "0.3", "l": "0.2"},
        },
        {
            "id": "1002",
            "isResult": True,
            "h": {"id": "3", "title": "Wolverhampton Wanderers", "short_title": "WOL"},
            "a": {"id": "4", "title": "Chelsea", "short_title": "CHE"},
            "goals": {"h": "0", "a": "3"},
            "xG": {"h": "0.45", "a": "2.10"},
            "datetime": "2024-08-17 17:30:00",
            "forecast": {"w": "0.2", "d": "0.3", "l": "0.5"},
        },
    ],
    "teams": {},
    "players": [],
}


def test_league_map_has_all_five():
    assert set(LEAGUE_MAP.keys()) == {"EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"}
    assert LEAGUE_MAP["EPL"] == "E0"
    assert LEAGUE_MAP["La_Liga"] == "SP1"


def test_parse_matches_extracts_fields():
    rows = parse_matches(SAMPLE_API_RESPONSE["dates"], division="E0")
    assert len(rows) == 2

    row = rows[0]
    assert row["division"] == "E0"
    assert row["match_date"] == "2024-08-17"
    assert row["home_team"] == "Arsenal"
    assert row["away_team"] == "Manchester City"
    assert row["home_xg"] == pytest.approx(1.85)
    assert row["away_xg"] == pytest.approx(1.23)
    assert row["home_goals"] == 2
    assert row["away_goals"] == 1
    assert row["source"] == "understat"


def test_parse_matches_raw_team_names():
    rows = parse_matches(SAMPLE_API_RESPONSE["dates"], division="E0")
    assert rows[1]["home_team"] == "Wolverhampton Wanderers"


def test_parse_matches_skips_unplayed():
    dates = [
        {
            "id": "9999",
            "isResult": False,
            "h": {"id": "1", "title": "A", "short_title": "A"},
            "a": {"id": "2", "title": "B", "short_title": "B"},
            "goals": {"h": "0", "a": "0"},
            "xG": {"h": "0", "a": "0"},
            "datetime": "2025-05-30 15:00:00",
            "forecast": {"w": "0.5", "d": "0.3", "l": "0.2"},
        }
    ]
    rows = parse_matches(dates, division="E0")
    assert len(rows) == 0


def test_fetch_league_season():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_API_RESPONSE

    with patch("backend.etl.understat.httpx.get", return_value=mock_response) as mock_get:
        result = fetch_league_season("EPL", 2024)

    assert result == SAMPLE_API_RESPONSE
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert "getLeagueData/EPL/2024" in call_args[0][0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_understat.py -v`
Expected: FAIL — `cannot import name 'LEAGUE_MAP'`

- [ ] **Step 3: Implement understat scraper**

```python
# backend/etl/understat.py
import asyncio
import logging
import time
from typing import Any

import httpx

from backend.db.client import get_supabase
from backend.services.teams import TeamNormalizer

logger = logging.getLogger(__name__)

LEAGUE_MAP = {
    "EPL": "E0",
    "La_Liga": "SP1",
    "Bundesliga": "D1",
    "Serie_A": "I1",
    "Ligue_1": "F1",
}

UNDERSTAT_BASE = "https://understat.com"
REQUEST_DELAY = 1.5


def fetch_league_season(league: str, season: int) -> dict[str, Any]:
    url = f"{UNDERSTAT_BASE}/getLeagueData/{league}/{season}"
    response = httpx.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Referer": f"{UNDERSTAT_BASE}/league/{league}/{season}",
            "X-Requested-With": "XMLHttpRequest",
        },
        follow_redirects=True,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def parse_matches(dates: list[dict], division: str) -> list[dict]:
    rows = []
    for match in dates:
        if not match.get("isResult"):
            continue
        dt = match["datetime"][:10]
        rows.append(
            {
                "division": division,
                "match_date": dt,
                "home_team": match["h"]["title"],
                "away_team": match["a"]["title"],
                "home_xg": float(match["xG"]["h"]),
                "away_xg": float(match["xG"]["a"]),
                "home_goals": int(match["goals"]["h"]),
                "away_goals": int(match["goals"]["a"]),
                "source": "understat",
            }
        )
    return rows


def load_xg_records(records: list[dict], normalize: callable, batch_size: int = 500) -> int:
    client = get_supabase()
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        for r in batch:
            r["home_team"] = normalize(r["home_team"])
            r["away_team"] = normalize(r["away_team"])
        client.table("match_xg").upsert(
            batch,
            on_conflict="division,match_date,home_team,away_team",
        ).execute()
        total += len(batch)
        logger.info("Loaded xG batch %d-%d (%d total)", i, i + len(batch), total)
    return total


def scrape_all(
    start_season: int = 2014,
    end_season: int = 2024,
) -> dict:
    normalizer = TeamNormalizer()
    all_records: list[dict] = []

    for league, division in LEAGUE_MAP.items():
        for season in range(start_season, end_season + 1):
            logger.info("Fetching %s %d/%d", league, season, season + 1)
            try:
                data = fetch_league_season(league, season)
                matches = parse_matches(data["dates"], division)
                all_records.extend(matches)
                logger.info("  Got %d matches", len(matches))
            except Exception:
                logger.exception("  Failed %s %d", league, season)
            time.sleep(REQUEST_DELAY)

    loaded = load_xg_records(all_records, normalizer.normalize)
    return {"scraped": len(all_records), "loaded": loaded}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_understat.py -v`
Expected: 5 passed

- [ ] **Step 5: Run ruff**

Run: `ruff check . && ruff format --check .`

- [ ] **Step 6: Commit**

```bash
git add backend/etl/understat.py tests/test_understat.py
git commit -m "feat: add Understat xG scraper with JSON API"
```

---

## Task 3: Understat Runner + Team Reconciliation

**Files:**
- Create: `scripts/run_understat.py`
- Create: `scripts/reconcile_teams.py`

- [ ] **Step 1: Create runner script**

```python
# scripts/run_understat.py
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    from backend.etl.understat import scrape_all

    result = scrape_all()
    logging.info("Understat scrape result: %s", result)
    if result["loaded"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create reconciliation script**

```python
# scripts/reconcile_teams.py
import logging

import httpx

from backend.etl.understat import LEAGUE_MAP, fetch_league_season
from backend.services.teams import TeamNormalizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


def main():
    normalizer = TeamNormalizer()
    unmapped: dict[str, set[str]] = {}

    for league, division in LEAGUE_MAP.items():
        logging.info("Checking %s 2024...", league)
        data = fetch_league_season(league, 2024)
        for match in data["dates"]:
            for side in ["h", "a"]:
                name = match[side]["title"]
                canonical = normalizer.normalize(name)
                if canonical == name and name not in normalizer.all_canonical():
                    if league not in unmapped:
                        unmapped[league] = set()
                    unmapped[league].add(name)

    if unmapped:
        print("\n=== UNMAPPED TEAM NAMES ===")
        for league, names in sorted(unmapped.items()):
            print(f"\n{league}:")
            for name in sorted(names):
                print(f'  "{name}": "<canonical_name>",')
    else:
        print("\nAll team names are mapped!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add scripts/run_understat.py scripts/reconcile_teams.py
git commit -m "feat: add Understat runner and team reconciliation scripts"
```

- [ ] **Step 4: Run reconciliation to find unmapped names**

Run: `PYTHONPATH=. python3 scripts/reconcile_teams.py`

Add any missing aliases to `data/team_mappings.json` and commit.

- [ ] **Step 5: Run the real Understat scrape**

Run: `PYTHONPATH=. python3 scripts/run_understat.py`

Expected: ~20K xG records loaded to Supabase. Takes ~90 seconds.

- [ ] **Step 6: Commit mapping fixes**

```bash
git add data/team_mappings.json
git commit -m "fix: add missing Understat team name aliases"
```

---

## Task 4: Feature Engine

**Files:**
- Create: `backend/services/features.py`
- Create: `tests/test_features.py`
- Create: `scripts/run_features.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_features.py
import pandas as pd
import pytest

from backend.services.features import compute_team_features, compute_h2h_features


def _make_matches_df():
    """10 matches for 2 teams across 5 matchdays."""
    data = [
        {"division": "E0", "match_date": "2024-01-01", "home_team": "Arsenal", "away_team": "Chelsea",
         "ft_home_goals": 2, "ft_away_goals": 1, "ft_result": "H",
         "home_shots_target": 6, "away_shots_target": 3, "home_corners": 5, "away_corners": 3,
         "home_xg": 1.8, "away_xg": 0.9},
        {"division": "E0", "match_date": "2024-01-15", "home_team": "Chelsea", "away_team": "Arsenal",
         "ft_home_goals": 0, "ft_away_goals": 0, "ft_result": "D",
         "home_shots_target": 4, "away_shots_target": 5, "home_corners": 4, "away_corners": 6,
         "home_xg": 0.6, "away_xg": 0.8},
        {"division": "E0", "match_date": "2024-02-01", "home_team": "Arsenal", "away_team": "Liverpool",
         "ft_home_goals": 3, "ft_away_goals": 1, "ft_result": "H",
         "home_shots_target": 8, "away_shots_target": 4, "home_corners": 7, "away_corners": 2,
         "home_xg": 2.5, "away_xg": 1.1},
        {"division": "E0", "match_date": "2024-02-15", "home_team": "Liverpool", "away_team": "Chelsea",
         "ft_home_goals": 2, "ft_away_goals": 2, "ft_result": "D",
         "home_shots_target": 5, "away_shots_target": 5, "home_corners": 4, "away_corners": 4,
         "home_xg": 1.5, "away_xg": 1.5},
        {"division": "E0", "match_date": "2024-03-01", "home_team": "Chelsea", "away_team": "Liverpool",
         "ft_home_goals": 1, "ft_away_goals": 0, "ft_result": "H",
         "home_shots_target": 3, "away_shots_target": 2, "home_corners": 3, "away_corners": 5,
         "home_xg": 0.9, "away_xg": 0.4},
        {"division": "E0", "match_date": "2024-03-15", "home_team": "Arsenal", "away_team": "Chelsea",
         "ft_home_goals": 1, "ft_away_goals": 1, "ft_result": "D",
         "home_shots_target": 5, "away_shots_target": 4, "home_corners": 6, "away_corners": 3,
         "home_xg": 1.2, "away_xg": 1.0},
    ]
    return pd.DataFrame(data)


def test_compute_team_features_shape():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    assert "team" in result.columns
    assert "match_date" in result.columns
    assert "goals_scored_avg" in result.columns
    assert "goals_conceded_avg" in result.columns
    assert "xg_for_avg" in result.columns
    assert "win_rate" in result.columns
    assert "btts_rate" in result.columns
    assert "over25_rate" in result.columns
    # Each match produces 2 rows (one per team)
    assert len(result) == len(df) * 2


def test_no_data_leakage():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    arsenal = result[result["team"] == "Arsenal"].sort_values("match_date")
    first_row = arsenal.iloc[0]
    # First match for Arsenal: no prior data, so features should be NaN
    assert pd.isna(first_row["goals_scored_avg"])


def test_rolling_values_correct():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    arsenal = result[result["team"] == "Arsenal"].sort_values("match_date")

    # Arsenal's 3rd match (2024-02-01): prior matches are Jan-01 (scored 2) and Jan-15 (scored 0)
    third_match = arsenal.iloc[2]
    assert third_match["goals_scored_avg"] == pytest.approx(1.0)  # (2 + 0) / 2


def test_compute_h2h_features():
    df = _make_matches_df()
    h2h = compute_h2h_features(df, "Arsenal", "Chelsea")
    assert h2h["total_matches"] >= 2
    assert "arsenal_wins" in h2h
    assert "chelsea_wins" in h2h
    assert "draws" in h2h
    assert "avg_total_goals" in h2h
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_features.py -v`
Expected: FAIL — `cannot import name 'compute_team_features'`

- [ ] **Step 3: Implement feature engine**

```python
# backend/services/features.py
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

FEATURES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "features"


def _expand_to_team_rows(df: pd.DataFrame) -> pd.DataFrame:
    home = df.rename(columns={
        "home_team": "team", "away_team": "opponent",
        "ft_home_goals": "goals_scored", "ft_away_goals": "goals_conceded",
        "home_shots_target": "shots_target", "away_shots_target": "opp_shots_target",
        "home_corners": "corners", "away_corners": "opp_corners",
        "home_xg": "xg_for", "away_xg": "xg_against",
    }).assign(venue="home")

    away = df.rename(columns={
        "away_team": "team", "home_team": "opponent",
        "ft_away_goals": "goals_scored", "ft_home_goals": "goals_conceded",
        "away_shots_target": "shots_target", "home_shots_target": "opp_shots_target",
        "away_corners": "corners", "home_corners": "opp_corners",
        "away_xg": "xg_for", "home_xg": "xg_against",
    }).assign(venue="away")

    cols = [
        "division", "match_date", "team", "opponent", "venue",
        "goals_scored", "goals_conceded", "shots_target", "corners",
        "xg_for", "xg_against", "ft_result",
    ]
    home_out = home[[c for c in cols if c in home.columns]]
    away_out = away[[c for c in cols if c in away.columns]]

    combined = pd.concat([home_out, away_out], ignore_index=True)
    combined["match_date"] = pd.to_datetime(combined["match_date"])
    combined.sort_values(["team", "match_date"], inplace=True)

    combined["win"] = ((combined["venue"] == "home") & (combined["ft_result"] == "H")) | \
                      ((combined["venue"] == "away") & (combined["ft_result"] == "A"))
    combined["draw"] = combined["ft_result"] == "D"
    combined["btts"] = (combined["goals_scored"] > 0) & (combined["goals_conceded"] > 0)
    combined["over25"] = (combined["goals_scored"] + combined["goals_conceded"]) > 2.5

    return combined


def compute_team_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    expanded = _expand_to_team_rows(df)

    grouped = expanded.groupby("team")
    expanded["goals_scored_avg"] = grouped["goals_scored"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["goals_conceded_avg"] = grouped["goals_conceded"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["xg_for_avg"] = grouped["xg_for"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["xg_against_avg"] = grouped["xg_against"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["shots_target_avg"] = grouped["shots_target"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["corners_avg"] = grouped["corners"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["win_rate"] = grouped["win"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["draw_rate"] = grouped["draw"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["btts_rate"] = grouped["btts"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["over25_rate"] = grouped["over25"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["xg_diff_avg"] = expanded["xg_for_avg"] - expanded["xg_against_avg"]
    expanded["xg_overperformance"] = grouped.apply(
        lambda g: g["goals_scored"].shift(1).rolling(10, min_periods=1).mean()
        - g["xg_for"].shift(1).rolling(10, min_periods=1).mean()
    ).reset_index(level=0, drop=True)

    logger.info("Computed features for %d team-match rows", len(expanded))
    return expanded


def compute_h2h_features(df: pd.DataFrame, team_a: str, team_b: str) -> dict:
    mask = (
        ((df["home_team"] == team_a) & (df["away_team"] == team_b))
        | ((df["home_team"] == team_b) & (df["away_team"] == team_a))
    )
    h2h = df[mask].copy()
    if h2h.empty:
        return {
            "total_matches": 0,
            "arsenal_wins": 0,
            "chelsea_wins": 0,
            "draws": 0,
            "avg_total_goals": 0.0,
        }

    a_wins = len(
        h2h[((h2h["home_team"] == team_a) & (h2h["ft_result"] == "H"))
           | ((h2h["away_team"] == team_a) & (h2h["ft_result"] == "A"))]
    )
    b_wins = len(
        h2h[((h2h["home_team"] == team_b) & (h2h["ft_result"] == "H"))
           | ((h2h["away_team"] == team_b) & (h2h["ft_result"] == "A"))]
    )
    draws = len(h2h[h2h["ft_result"] == "D"])
    total_goals = (h2h["ft_home_goals"] + h2h["ft_away_goals"]).mean()

    return {
        "total_matches": len(h2h),
        f"{team_a.lower().replace(' ', '_')}_wins": a_wins,
        f"{team_b.lower().replace(' ', '_')}_wins": b_wins,
        "draws": draws,
        "avg_total_goals": round(float(total_goals), 2),
    }


def save_features(features_df: pd.DataFrame, path: Path | None = None) -> Path:
    if path is None:
        path = FEATURES_DIR / "team_features.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_parquet(path, index=False)
    logger.info("Saved %d rows to %s", len(features_df), path)
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_features.py -v`
Expected: 4 passed

- [ ] **Step 5: Create runner script**

```python
# scripts/run_features.py
import logging
import sys

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    from backend.db.client import get_supabase
    from backend.services.features import compute_team_features, save_features

    client = get_supabase()

    logging.info("Loading matches from Supabase...")
    matches_resp = client.table("matches").select("*").execute()
    matches_df = pd.DataFrame(matches_resp.data)
    logging.info("Loaded %d matches", len(matches_df))

    logging.info("Loading xG data from Supabase...")
    xg_resp = client.table("match_xg").select("*").execute()
    xg_df = pd.DataFrame(xg_resp.data)
    logging.info("Loaded %d xG records", len(xg_df))

    if not xg_df.empty:
        matches_df = matches_df.merge(
            xg_df[["division", "match_date", "home_team", "away_team", "home_xg", "away_xg"]],
            on=["division", "match_date", "home_team", "away_team"],
            how="left",
        )
    else:
        matches_df["home_xg"] = None
        matches_df["away_xg"] = None

    features = compute_team_features(matches_df, window=5)
    path = save_features(features)
    logging.info("Features saved to %s (%d rows)", path, len(features))


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run ruff**

Run: `ruff check . && ruff format --check .`

- [ ] **Step 7: Commit**

```bash
git add backend/services/features.py tests/test_features.py scripts/run_features.py
git commit -m "feat: add feature engine with rolling stats and H2H"
```

- [ ] **Step 8: Run the real feature generation**

Run: `PYTHONPATH=. python3 scripts/run_features.py`

Expected: Parquet file created at `data/features/team_features.parquet`.

---

## Task 5: Dashboard Data Access Layer

**Files:**
- Create: `dashboard/__init__.py`
- Create: `dashboard/data_access.py`

- [ ] **Step 1: Create data access module**

```python
# dashboard/data_access.py
import os
from pathlib import Path

import duckdb
import pandas as pd
from supabase import Client, create_client

FEATURES_PATH = Path(__file__).resolve().parent.parent / "data" / "features" / "team_features.parquet"

_supabase: Client | None = None


def get_supabase_client() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", "")),
        )
    return _supabase


def load_features(path: Path = FEATURES_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return duckdb.sql(f"SELECT * FROM '{path}'").df()


def load_matches(division: str | None = None, season: str | None = None) -> pd.DataFrame:
    client = get_supabase_client()
    query = client.table("matches").select("*")
    if division:
        query = query.eq("division", division)
    resp = query.execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        return df
    df["match_date"] = pd.to_datetime(df["match_date"])
    if season:
        start_year = int(season[:4])
        df = df[
            (df["match_date"] >= f"{start_year}-07-01")
            & (df["match_date"] < f"{start_year + 1}-07-01")
        ]
    return df


def load_xg(division: str | None = None) -> pd.DataFrame:
    client = get_supabase_client()
    query = client.table("match_xg").select("*")
    if division:
        query = query.eq("division", division)
    resp = query.execute()
    return pd.DataFrame(resp.data)


def get_seasons(division: str) -> list[str]:
    df = load_matches(division)
    if df.empty:
        return []
    df["year"] = df["match_date"].dt.year
    df["month"] = df["match_date"].dt.month
    df["season_start"] = df.apply(
        lambda r: r["year"] if r["month"] >= 7 else r["year"] - 1, axis=1
    )
    starts = sorted(df["season_start"].unique(), reverse=True)
    return [f"{y}/{y + 1}" for y in starts]


def get_teams(division: str) -> list[str]:
    df = load_matches(division)
    if df.empty:
        return []
    teams = sorted(set(df["home_team"].unique()) | set(df["away_team"].unique()))
    return teams


DIVISION_NAMES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
    "EC": "Champions League",
}
```

- [ ] **Step 2: Create empty __init__.py**

```bash
touch dashboard/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/__init__.py dashboard/data_access.py
git commit -m "feat: add dashboard data access layer with DuckDB + Supabase"
```

---

## Task 6: Dashboard Charts + Tables Components

**Files:**
- Create: `dashboard/components/__init__.py`
- Create: `dashboard/components/charts.py`
- Create: `dashboard/components/tables.py`

- [ ] **Step 1: Create chart builders**

```python
# dashboard/components/charts.py
import plotly.graph_objects as go
import pandas as pd


def xg_vs_goals_chart(df: pd.DataFrame, team: str) -> go.Figure:
    team_df = df[df["team"] == team].sort_values("match_date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=team_df["match_date"], y=team_df["goals_scored"],
        name="Goals", mode="lines+markers", line={"color": "#2ecc71"},
    ))
    fig.add_trace(go.Scatter(
        x=team_df["match_date"], y=team_df["xg_for"],
        name="xG", mode="lines+markers", line={"color": "#3498db", "dash": "dash"},
    ))
    fig.update_layout(
        title=f"{team} — Goals vs xG", xaxis_title="Date", yaxis_title="Goals / xG",
        template="plotly_dark", height=400,
    )
    return fig


def home_away_chart(df: pd.DataFrame, team: str) -> go.Figure:
    home = df[(df["team"] == team) & (df["venue"] == "home")]
    away = df[(df["team"] == team) & (df["venue"] == "away")]

    home_w = home["win"].sum()
    home_d = home["draw"].sum()
    home_l = len(home) - home_w - home_d
    away_w = away["win"].sum()
    away_d = away["draw"].sum()
    away_l = len(away) - away_w - away_d

    fig = go.Figure(data=[
        go.Bar(name="Wins", x=["Home", "Away"], y=[home_w, away_w], marker_color="#2ecc71"),
        go.Bar(name="Draws", x=["Home", "Away"], y=[home_d, away_d], marker_color="#f39c12"),
        go.Bar(name="Losses", x=["Home", "Away"], y=[home_l, away_l], marker_color="#e74c3c"),
    ])
    fig.update_layout(
        barmode="stack", title=f"{team} — Home vs Away",
        template="plotly_dark", height=350,
    )
    return fig


def radar_chart(stats_a: dict, stats_b: dict, team_a: str, team_b: str) -> go.Figure:
    categories = list(stats_a.keys())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=list(stats_a.values()), theta=categories, fill="toself", name=team_a,
    ))
    fig.add_trace(go.Scatterpolar(
        r=list(stats_b.values()), theta=categories, fill="toself", name=team_b,
    ))
    fig.update_layout(
        polar={"radialaxis": {"visible": True}},
        title=f"{team_a} vs {team_b}", template="plotly_dark", height=450,
    )
    return fig
```

- [ ] **Step 2: Create table formatters**

```python
# dashboard/components/tables.py
import pandas as pd


def standings_table(matches_df: pd.DataFrame, xg_df: pd.DataFrame | None = None) -> pd.DataFrame:
    teams = sorted(set(matches_df["home_team"]) | set(matches_df["away_team"]))
    rows = []
    for team in teams:
        home = matches_df[matches_df["home_team"] == team]
        away = matches_df[matches_df["away_team"] == team]
        hw = len(home[home["ft_result"] == "H"])
        hd = len(home[home["ft_result"] == "D"])
        hl = len(home[home["ft_result"] == "A"])
        aw = len(away[away["ft_result"] == "A"])
        ad = len(away[away["ft_result"] == "D"])
        al = len(away[away["ft_result"] == "H"])

        gf = int(home["ft_home_goals"].sum() + away["ft_away_goals"].sum())
        ga = int(home["ft_away_goals"].sum() + away["ft_home_goals"].sum())

        p = len(home) + len(away)
        w = hw + aw
        d = hd + ad
        l_count = hl + al
        pts = w * 3 + d

        row = {"Team": team, "P": p, "W": w, "D": d, "L": l_count,
               "GF": gf, "GA": ga, "GD": gf - ga, "Pts": pts}

        if xg_df is not None and not xg_df.empty:
            xg_home = xg_df[xg_df["home_team"] == team]
            xg_away = xg_df[xg_df["away_team"] == team]
            xg_for = float(xg_home["home_xg"].sum() + xg_away["away_xg"].sum())
            xg_against = float(xg_home["away_xg"].sum() + xg_away["home_xg"].sum())
            row["xG"] = round(xg_for, 1)
            row["xGA"] = round(xg_against, 1)
            row["xGD"] = round(xg_for - xg_against, 1)

        rows.append(row)

    result = pd.DataFrame(rows)
    result.sort_values("Pts", ascending=False, inplace=True)
    result.insert(0, "Pos", range(1, len(result) + 1))
    return result


def form_indicator(matches_df: pd.DataFrame, team: str, n: int = 5) -> str:
    all_matches = pd.concat([
        matches_df[matches_df["home_team"] == team].assign(
            result=matches_df["ft_result"].map({"H": "W", "D": "D", "A": "L"})
        ),
        matches_df[matches_df["away_team"] == team].assign(
            result=matches_df["ft_result"].map({"A": "W", "D": "D", "H": "L"})
        ),
    ])
    all_matches = all_matches.sort_values("match_date", ascending=False)
    last_n = all_matches.head(n)["result"].tolist()
    return " ".join(last_n)


def last_n_results(matches_df: pd.DataFrame, team: str, n: int = 10) -> pd.DataFrame:
    home = matches_df[matches_df["home_team"] == team].copy()
    home["opponent"] = home["away_team"]
    home["score"] = home["ft_home_goals"].astype(str) + "-" + home["ft_away_goals"].astype(str)
    home["venue"] = "H"

    away = matches_df[matches_df["away_team"] == team].copy()
    away["opponent"] = away["home_team"]
    away["score"] = away["ft_away_goals"].astype(str) + "-" + away["ft_home_goals"].astype(str)
    away["venue"] = "A"

    combined = pd.concat([home, away]).sort_values("match_date", ascending=False)
    return combined[["match_date", "opponent", "score", "venue", "ft_result"]].head(n)
```

- [ ] **Step 3: Commit**

```bash
mkdir -p dashboard/components
touch dashboard/components/__init__.py
git add dashboard/components/__init__.py dashboard/components/charts.py dashboard/components/tables.py
git commit -m "feat: add dashboard chart and table components"
```

---

## Task 7: Streamlit App + League Overview Page

**Files:**
- Create: `dashboard/app.py`
- Create: `dashboard/pages/1_league_overview.py`

- [ ] **Step 1: Create main app entry**

```python
# dashboard/app.py
import streamlit as st

st.set_page_config(
    page_title="Master Prediction",
    page_icon="⚽",
    layout="wide",
)

st.title("Master Prediction")
st.markdown("### Betting Intelligence Platform")
st.markdown("""
Select a page from the sidebar:

- **League Overview** — Enriched standings with xG and form
- **Team Analysis** — Deep dive into a single team
- **Match Comparator** — Head-to-head comparison
""")
```

- [ ] **Step 2: Create League Overview page**

```python
# dashboard/pages/1_league_overview.py
import streamlit as st

from dashboard.data_access import DIVISION_NAMES, get_seasons, load_matches, load_xg
from dashboard.components.tables import form_indicator, standings_table

st.set_page_config(page_title="League Overview", layout="wide")
st.title("League Overview")

col1, col2 = st.columns(2)
with col1:
    league = st.selectbox("League", list(DIVISION_NAMES.keys()),
                          format_func=lambda x: DIVISION_NAMES[x])
with col2:
    seasons = get_seasons(league)
    season = st.selectbox("Season", seasons if seasons else ["No data"])

if season and season != "No data":
    matches = load_matches(division=league, season=season)
    xg = load_xg(division=league)

    if not matches.empty:
        if not xg.empty:
            xg["match_date"] = xg["match_date"].astype(str)
            matches["match_date_str"] = matches["match_date"].astype(str)
            start_year = int(season[:4])
            xg = xg[
                (xg["match_date"] >= f"{start_year}-07-01")
                & (xg["match_date"] < f"{start_year + 1}-07-01")
            ]

        table = standings_table(matches, xg if not xg.empty else None)

        form_col = []
        for team in table["Team"]:
            form_col.append(form_indicator(matches, team))
        table["Form (last 5)"] = form_col

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "xGD": st.column_config.NumberColumn(format="%.1f"),
                "xG": st.column_config.NumberColumn(format="%.1f"),
                "xGA": st.column_config.NumberColumn(format="%.1f"),
            },
        )
    else:
        st.warning("No match data for this season.")
```

- [ ] **Step 3: Create pages directory**

```bash
mkdir -p dashboard/pages
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/app.py dashboard/pages/1_league_overview.py
git commit -m "feat: add Streamlit app with League Overview page"
```

---

## Task 8: Team Analysis Page

**Files:**
- Create: `dashboard/pages/2_team_analysis.py`

- [ ] **Step 1: Create Team Analysis page**

```python
# dashboard/pages/2_team_analysis.py
import streamlit as st

from dashboard.components.charts import home_away_chart, xg_vs_goals_chart
from dashboard.components.tables import last_n_results
from dashboard.data_access import DIVISION_NAMES, get_seasons, get_teams, load_features, load_matches, load_xg

st.set_page_config(page_title="Team Analysis", layout="wide")
st.title("Team Analysis")

col1, col2, col3 = st.columns(3)
with col1:
    league = st.selectbox("League", list(DIVISION_NAMES.keys()),
                          format_func=lambda x: DIVISION_NAMES[x])
with col2:
    seasons = get_seasons(league)
    season = st.selectbox("Season", seasons if seasons else ["No data"])
with col3:
    teams = get_teams(league)
    team = st.selectbox("Team", teams if teams else ["No data"])

if team and team != "No data" and season != "No data":
    matches = load_matches(division=league, season=season)
    features = load_features()

    if not matches.empty:
        home = matches[matches["home_team"] == team]
        away = matches[matches["away_team"] == team]

        total_p = len(home) + len(away)
        total_w = len(home[home["ft_result"] == "H"]) + len(away[away["ft_result"] == "A"])
        total_d = len(home[home["ft_result"] == "D"]) + len(away[away["ft_result"] == "D"])
        total_l = total_p - total_w - total_d
        gf = int(home["ft_home_goals"].sum() + away["ft_away_goals"].sum())
        ga = int(home["ft_away_goals"].sum() + away["ft_home_goals"].sum())

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("P", total_p)
        m2.metric("W", total_w)
        m3.metric("D", total_d)
        m4.metric("L", total_l)
        m5.metric("GF", gf)
        m6.metric("GA", ga)

        if not features.empty:
            team_features = features[features["team"] == team].copy()
            if not team_features.empty:
                team_features["match_date"] = team_features["match_date"].astype(str)
                start_year = int(season[:4])
                team_features = team_features[
                    (team_features["match_date"] >= f"{start_year}-07-01")
                    & (team_features["match_date"] < f"{start_year + 1}-07-01")
                ]
                if not team_features.empty:
                    chart_col1, chart_col2 = st.columns(2)
                    with chart_col1:
                        st.plotly_chart(xg_vs_goals_chart(team_features, team),
                                       use_container_width=True)
                    with chart_col2:
                        st.plotly_chart(home_away_chart(team_features, team),
                                       use_container_width=True)

        st.subheader("Last 10 Results")
        results = last_n_results(matches, team, n=10)
        st.dataframe(results, use_container_width=True, hide_index=True)
    else:
        st.warning("No match data available.")
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/pages/2_team_analysis.py
git commit -m "feat: add Team Analysis dashboard page"
```

---

## Task 9: Match Comparator Page

**Files:**
- Create: `dashboard/pages/3_match_comparator.py`

- [ ] **Step 1: Create Match Comparator page**

```python
# dashboard/pages/3_match_comparator.py
import pandas as pd
import streamlit as st

from dashboard.components.charts import radar_chart
from dashboard.data_access import DIVISION_NAMES, get_teams, load_features, load_matches
from backend.services.features import compute_h2h_features

st.set_page_config(page_title="Match Comparator", layout="wide")
st.title("Match Comparator")

col1, col2, col3 = st.columns(3)
with col1:
    league = st.selectbox("League", list(DIVISION_NAMES.keys()),
                          format_func=lambda x: DIVISION_NAMES[x])
with col2:
    teams = get_teams(league)
    team_a = st.selectbox("Team A", teams if teams else ["No data"])
with col3:
    other_teams = [t for t in teams if t != team_a] if teams else ["No data"]
    team_b = st.selectbox("Team B", other_teams)

if team_a != "No data" and team_b != "No data":
    matches = load_matches(division=league)
    features = load_features()

    if not matches.empty:
        h2h = compute_h2h_features(matches, team_a, team_b)

        st.subheader("Head to Head")
        h_col1, h_col2, h_col3, h_col4 = st.columns(4)
        h_col1.metric("Total Matches", h2h["total_matches"])
        a_key = f"{team_a.lower().replace(' ', '_')}_wins"
        b_key = f"{team_b.lower().replace(' ', '_')}_wins"
        h_col2.metric(f"{team_a} Wins", h2h.get(a_key, 0))
        h_col3.metric(f"{team_b} Wins", h2h.get(b_key, 0))
        h_col4.metric("Draws", h2h["draws"])

        if not features.empty:
            fa = features[features["team"] == team_a]
            fb = features[features["team"] == team_b]

            if not fa.empty and not fb.empty:
                latest_a = fa.sort_values("match_date").iloc[-1]
                latest_b = fb.sort_values("match_date").iloc[-1]

                st.subheader("Current Form Comparison")
                compare_cols = ["goals_scored_avg", "xg_for_avg", "goals_conceded_avg",
                                "shots_target_avg", "corners_avg", "win_rate"]
                labels = ["Goals", "xG", "Defense", "Shots", "Corners", "Win %"]

                stats_a = {}
                stats_b = {}
                for col, label in zip(compare_cols, labels):
                    val_a = latest_a.get(col, 0)
                    val_b = latest_b.get(col, 0)
                    stats_a[label] = float(val_a) if pd.notna(val_a) else 0.0
                    stats_b[label] = float(val_b) if pd.notna(val_b) else 0.0

                st.plotly_chart(radar_chart(stats_a, stats_b, team_a, team_b),
                               use_container_width=True)

        st.subheader("H2H Match History")
        h2h_matches = matches[
            ((matches["home_team"] == team_a) & (matches["away_team"] == team_b))
            | ((matches["home_team"] == team_b) & (matches["away_team"] == team_a))
        ].sort_values("match_date", ascending=False)

        if not h2h_matches.empty:
            display_df = h2h_matches[
                ["match_date", "home_team", "away_team", "ft_home_goals", "ft_away_goals", "ft_result"]
            ].copy()
            display_df.columns = ["Date", "Home", "Away", "HG", "AG", "Result"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No head-to-head matches found.")
    else:
        st.warning("No match data available.")
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/pages/3_match_comparator.py
git commit -m "feat: add Match Comparator dashboard page"
```

---

## Task 10: Update ETL Pipeline + CI

**Files:**
- Modify: `.github/workflows/etl.yml`

- [ ] **Step 1: Update ETL workflow to include Understat + features**

```yaml
# .github/workflows/etl.yml
name: ETL Pipeline

on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:

jobs:
  run-etl:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run match ETL pipeline
        run: PYTHONPATH=. python scripts/run_etl.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Run Understat xG scraper (current season only)
        run: PYTHONPATH=. python scripts/run_understat.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Generate features
        run: PYTHONPATH=. python scripts/run_features.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Commit updated features
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/features/ -f
          git diff --cached --quiet || git commit -m "data: update features [skip ci]"
          git push
```

- [ ] **Step 2: Update run_understat.py to support current-season-only mode**

Modify `scripts/run_understat.py`:

```python
# scripts/run_understat.py
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    from backend.etl.understat import scrape_all

    current_only = "--current" in sys.argv
    if current_only:
        result = scrape_all(start_season=2024, end_season=2024)
    else:
        result = scrape_all()

    logging.info("Understat scrape result: %s", result)
    if result["loaded"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Update the ETL workflow step to use `--current` flag:

```yaml
      - name: Run Understat xG scraper (current season only)
        run: PYTHONPATH=. python scripts/run_understat.py --current
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/etl.yml scripts/run_understat.py
git commit -m "ci: extend ETL pipeline with Understat + features + auto-commit"
```

---

## Task 11: Final Verification + Push

- [ ] **Step 1: Run all tests**

Run: `PYTHONPATH=. python3 -m pytest tests/ -v`
Expected: All tests pass (18 existing + new tests)

- [ ] **Step 2: Run ruff**

Run: `ruff check . && ruff format --check .`

- [ ] **Step 3: Test dashboard locally**

Run: `cd "/Users/ivanmr/Documents/Documentos IMR/Personal IMR/IA/Golpredictor" && PYTHONPATH=. streamlit run dashboard/app.py`

Verify:
- League Overview shows standings with xG columns
- Team Analysis shows charts and recent results
- Match Comparator shows H2H and radar chart

- [ ] **Step 4: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 5: Verify CI passes**

Check GitHub Actions → CI workflow passes on the push.

---

## Verification Checklist

- [ ] `match_xg` table exists in Supabase with ~20K rows
- [ ] `data/features/team_features.parquet` exists locally
- [ ] All tests pass (both old and new)
- [ ] Ruff passes
- [ ] Dashboard runs locally with 3 working pages
- [ ] ETL workflow includes Understat + features steps
- [ ] GitHub Secrets are configured
