# Phase 4: Betting Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a value bet detection engine that compares XGBoost model probabilities against real bookmaker odds, generates daily picks with suggested stakes (1u-3u), auto-resolves results, and displays everything in a Streamlit performance dashboard.

**Architecture:** Odds are fetched from The Odds API (free tier, 500 req/month) and stored in the existing `matches` table. A value engine compares model probabilities vs implied probabilities from odds, generating picks stored in a new `value_bets` table. A tracker resolves picks when match results arrive. Dashboard page shows active picks and historical performance.

**Tech Stack:** Python 3.13, httpx, Supabase (PostgreSQL), Streamlit, plotly, pandas

**Design Spec:** `docs/superpowers/specs/2026-05-21-phase4-betting-intelligence-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/etl/odds.py` | Fetch odds from The Odds API, parse, update matches table |
| Create | `backend/betting/__init__.py` | Package init |
| Create | `backend/betting/value.py` | Calculate edge, generate picks, classify stakes |
| Create | `backend/betting/tracker.py` | Resolve picks, calculate performance metrics |
| Create | `backend/db/schema_value_bets.sql` | SQL for value_bets table creation |
| Create | `scripts/run_odds.py` | CLI entry point for odds sync |
| Create | `scripts/run_value_bets.py` | CLI entry point for value bet generation |
| Create | `scripts/run_resolve_picks.py` | CLI entry point for pick resolution |
| Create | `dashboard/components/value_bets.py` | Format picks and resolved bets tables |
| Create | `dashboard/components/performance.py` | Profit chart and KPI functions |
| Create | `dashboard/pages/5_value_bets.py` | Streamlit page for value bets |
| Create | `tests/test_odds.py` | Tests for odds module |
| Create | `tests/test_value.py` | Tests for value bet engine |
| Create | `tests/test_tracker.py` | Tests for performance tracker |
| Modify | `.github/workflows/etl.yml` | Add 3 new pipeline steps |

---

### Task 1: DB Schema — `value_bets` Table

**Files:**
- Create: `backend/db/schema_value_bets.sql`

- [ ] **Step 1: Create the SQL schema file**

```sql
CREATE TABLE IF NOT EXISTS value_bets (
    id BIGSERIAL PRIMARY KEY,
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    division TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    model_prob REAL NOT NULL,
    implied_prob REAL NOT NULL,
    edge REAL NOT NULL,
    odd REAL NOT NULL,
    bookmaker TEXT,
    stake INTEGER NOT NULL,
    expected_value REAL NOT NULL,
    confidence TEXT NOT NULL,
    model_variant TEXT NOT NULL,
    result TEXT,
    profit REAL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    UNIQUE(match_date, home_team, away_team, market)
);

CREATE INDEX IF NOT EXISTS idx_value_bets_date ON value_bets(match_date);
CREATE INDEX IF NOT EXISTS idx_value_bets_result ON value_bets(result);
CREATE INDEX IF NOT EXISTS idx_value_bets_pending ON value_bets(result) WHERE result IS NULL;
```

Write this to `backend/db/schema_value_bets.sql`.

- [ ] **Step 2: Run SQL in Supabase**

This is a manual step. Go to the Supabase SQL editor and run the contents of `backend/db/schema_value_bets.sql`. Verify the table and indexes were created.

- [ ] **Step 3: Commit**

```bash
git add backend/db/schema_value_bets.sql
git commit -m "feat: add value_bets table schema"
```

---

### Task 2: Odds Scraper — `backend/etl/odds.py`

**Files:**
- Create: `backend/etl/odds.py`
- Create: `tests/test_odds.py`

- [ ] **Step 1: Write tests for odds parsing and fetching**

Create `tests/test_odds.py`:

```python
from unittest.mock import MagicMock, patch

from backend.etl.odds import (
    SPORT_KEY_MAP,
    parse_odds,
    run_odds_sync,
)
from backend.services.teams import TeamNormalizer


SAMPLE_API_RESPONSE = [
    {
        "id": "abc123",
        "sport_key": "soccer_epl",
        "commence_time": "2026-05-25T15:00:00Z",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "bookmakers": [
            {
                "key": "pinnacle",
                "title": "Pinnacle",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.10},
                            {"name": "Chelsea", "price": 3.50},
                            {"name": "Draw", "price": 3.20},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": 2.5, "price": 1.90},
                            {"name": "Under", "point": 2.5, "price": 1.95},
                        ],
                    },
                ],
            },
            {
                "key": "bet365",
                "title": "Bet365",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.05},
                            {"name": "Chelsea", "price": 3.40},
                            {"name": "Draw", "price": 3.30},
                        ],
                    },
                ],
            },
        ],
    }
]


def test_sport_key_map_covers_all_divisions():
    expected = {"E0", "SP1", "D1", "I1", "F1", "EC", "WC"}
    assert set(SPORT_KEY_MAP.values()) == expected


def test_parse_odds_extracts_best_odds():
    normalizer = TeamNormalizer()
    records = parse_odds(SAMPLE_API_RESPONSE, "E0", normalizer)

    assert len(records) == 1
    r = records[0]
    assert r["home_team"] == "Arsenal"
    assert r["away_team"] == "Chelsea"
    assert r["division"] == "E0"
    assert r["match_date"] == "2026-05-25"
    assert r["odd_home"] == 2.10
    assert r["odd_away"] == 3.50
    assert r["odd_draw"] == 3.30
    assert r["odd_over25"] == 1.90
    assert r["odd_under25"] == 1.95
    assert r["bookmaker_h2h"] == "pinnacle"


def test_parse_odds_missing_totals():
    events = [
        {
            "id": "xyz",
            "sport_key": "soccer_epl",
            "commence_time": "2026-05-25T15:00:00Z",
            "home_team": "Liverpool",
            "away_team": "Everton",
            "bookmakers": [
                {
                    "key": "bet365",
                    "title": "Bet365",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Liverpool", "price": 1.50},
                                {"name": "Everton", "price": 6.00},
                                {"name": "Draw", "price": 4.20},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    normalizer = TeamNormalizer()
    records = parse_odds(events, "E0", normalizer)
    assert len(records) == 1
    assert records[0]["odd_over25"] is None
    assert records[0]["odd_under25"] is None


def test_parse_odds_empty_bookmakers():
    events = [
        {
            "id": "xyz",
            "sport_key": "soccer_epl",
            "commence_time": "2026-05-25T15:00:00Z",
            "home_team": "Liverpool",
            "away_team": "Everton",
            "bookmakers": [],
        }
    ]
    normalizer = TeamNormalizer()
    records = parse_odds(events, "E0", normalizer)
    assert len(records) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_odds.py -v`
Expected: FAIL — `ImportError: cannot import name 'SPORT_KEY_MAP' from 'backend.etl.odds'`

- [ ] **Step 3: Implement `backend/etl/odds.py`**

```python
import logging
import os
import time

import httpx

from backend.services.teams import TeamNormalizer

logger = logging.getLogger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

SPORT_KEY_MAP = {
    "soccer_epl": "E0",
    "soccer_spain_la_liga": "SP1",
    "soccer_germany_bundesliga": "D1",
    "soccer_italy_serie_a": "I1",
    "soccer_france_ligue_one": "F1",
    "soccer_uefa_champs_league": "EC",
    "soccer_fifa_world_cup": "WC",
}


def _get_token() -> str:
    token = os.environ.get("ODDS_API_KEY", "")
    if not token:
        raise RuntimeError("ODDS_API_KEY environment variable not set")
    return token


def fetch_odds(sport_key: str, token: str) -> list[dict]:
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": token,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
    }
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    events = resp.json()
    logger.info("Fetched %d events for %s", len(events), sport_key)
    return events


def _best_odds_for_market(bookmakers: list[dict], market_key: str) -> tuple[dict, str]:
    best: dict = {}
    best_bookmaker = ""

    pinnacle_found = False
    for bk in bookmakers:
        if bk["key"] == "pinnacle":
            for mkt in bk.get("markets", []):
                if mkt["key"] == market_key:
                    pinnacle_found = True
                    best_bookmaker = "pinnacle"
                    for outcome in mkt["outcomes"]:
                        best[outcome["name"]] = outcome["price"]
                        if "point" in outcome:
                            best[f"{outcome['name']}_point"] = outcome["point"]
                    break
            break

    if not pinnacle_found:
        per_outcome: dict[str, tuple[float, str]] = {}
        for bk in bookmakers:
            for mkt in bk.get("markets", []):
                if mkt["key"] == market_key:
                    for outcome in mkt["outcomes"]:
                        name = outcome["name"]
                        price = outcome["price"]
                        if name not in per_outcome or price > per_outcome[name][0]:
                            per_outcome[name] = (price, bk["key"])
                            if "point" in outcome:
                                best[f"{name}_point"] = outcome["point"]
        if per_outcome:
            best_bookmaker = max(
                set(bk for _, bk in per_outcome.values()),
                key=lambda b: sum(1 for _, bk in per_outcome.values() if bk == b),
            )
            for name, (price, _) in per_outcome.items():
                best[name] = price

    return best, best_bookmaker


def parse_odds(events: list[dict], division: str, normalizer: TeamNormalizer) -> list[dict]:
    records = []
    for event in events:
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        home_raw = event["home_team"]
        away_raw = event["away_team"]
        match_date = event["commence_time"][:10]

        h2h, h2h_bk = _best_odds_for_market(bookmakers, "h2h")
        if not h2h:
            continue

        totals, totals_bk = _best_odds_for_market(bookmakers, "totals")

        records.append({
            "match_date": match_date,
            "home_team": normalizer.normalize(home_raw),
            "away_team": normalizer.normalize(away_raw),
            "division": division,
            "odd_home": h2h.get(home_raw),
            "odd_draw": h2h.get("Draw"),
            "odd_away": h2h.get(away_raw),
            "odd_over25": totals.get("Over") if totals else None,
            "odd_under25": totals.get("Under") if totals else None,
            "bookmaker_h2h": h2h_bk,
            "bookmaker_totals": totals_bk if totals else None,
        })

    return records


def update_match_odds(records: list[dict]) -> int:
    if not records:
        return 0

    from backend.db.client import get_supabase

    client = get_supabase()
    updated = 0

    for r in records:
        update_data = {
            "odd_home": r["odd_home"],
            "odd_draw": r["odd_draw"],
            "odd_away": r["odd_away"],
            "odd_over25": r["odd_over25"],
            "odd_under25": r["odd_under25"],
        }
        resp = (
            client.table("matches")
            .update(update_data)
            .eq("division", r["division"])
            .eq("match_date", r["match_date"])
            .eq("home_team", r["home_team"])
            .eq("away_team", r["away_team"])
            .is_("ft_result", "null")
            .execute()
        )
        if resp.data:
            updated += 1

    logger.info("Updated odds for %d matches", updated)
    return updated


def run_odds_sync() -> dict:
    token = _get_token()
    normalizer = TeamNormalizer()

    from backend.db.client import get_supabase

    client = get_supabase()

    total_updated = 0
    total_events = 0

    for sport_key, division in SPORT_KEY_MAP.items():
        pending = (
            client.table("matches")
            .select("id", count="exact")
            .eq("division", division)
            .is_("ft_result", "null")
            .execute()
        )
        if not pending.count:
            logger.info("No pending fixtures for %s (%s), skipping", division, sport_key)
            continue

        try:
            events = fetch_odds(sport_key, token)
        except httpx.HTTPStatusError as e:
            logger.warning("Failed to fetch odds for %s: %s", sport_key, e)
            time.sleep(1)
            continue

        records = parse_odds(events, division, normalizer)
        updated = update_match_odds(records)
        total_events += len(events)
        total_updated += updated
        logger.info("%s: %d events, %d matches updated", division, len(events), updated)
        time.sleep(1)

    return {"total_events": total_events, "total_updated": total_updated}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_odds.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run ruff**

Run: `PYTHONPATH=. python3 -m ruff check backend/etl/odds.py tests/test_odds.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add backend/etl/odds.py tests/test_odds.py
git commit -m "feat: add odds scraper for The Odds API"
```

---

### Task 3: Value Bet Engine — `backend/betting/value.py`

**Files:**
- Create: `backend/betting/__init__.py`
- Create: `backend/betting/value.py`
- Create: `tests/test_value.py`

- [ ] **Step 1: Write tests for value bet engine**

Create `tests/test_value.py`:

```python
from backend.betting.value import calculate_edge, classify_stake, generate_picks


def test_calculate_edge_positive():
    result = calculate_edge(0.55, 2.10)
    assert round(result["implied_prob"], 4) == round(1 / 2.10, 4)
    assert round(result["edge"], 4) == round(0.55 - 1 / 2.10, 4)
    assert round(result["expected_value"], 4) == round((0.55 * 2.10) - 1, 4)


def test_calculate_edge_negative():
    result = calculate_edge(0.30, 2.10)
    assert result["edge"] < 0


def test_classify_stake_3u():
    assert classify_stake(0.12, "alta") == 3


def test_classify_stake_2u():
    assert classify_stake(0.08, "media") == 2
    assert classify_stake(0.08, "alta") == 2


def test_classify_stake_1u():
    assert classify_stake(0.06, "baja") == 1


def test_classify_stake_skip():
    assert classify_stake(0.04, "alta") == 0
    assert classify_stake(0.05, "media") == 0


def test_classify_stake_2u_requires_media():
    assert classify_stake(0.08, "baja") == 1


def test_classify_stake_3u_requires_alta():
    assert classify_stake(0.12, "media") == 2


def test_generate_picks_basic():
    predictions = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "prob_home": 0.55,
            "prob_draw": 0.25,
            "prob_away": 0.20,
            "prob_over25": 0.65,
            "prob_btts": 0.50,
            "confidence": "alta",
            "model_variant": "premium",
        }
    ]
    matches_with_odds = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "odd_home": 2.10,
            "odd_draw": 3.50,
            "odd_away": 4.50,
            "odd_over25": 1.70,
            "odd_under25": 2.15,
        }
    ]
    picks = generate_picks(predictions, matches_with_odds)
    assert len(picks) > 0
    for pick in picks:
        assert pick["edge"] > 0.05
        assert pick["stake"] >= 1
        assert pick["market"] in [
            "1x2_home", "1x2_draw", "1x2_away", "over25", "under25"
        ]


def test_generate_picks_no_edge():
    predictions = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "prob_home": 0.40,
            "prob_draw": 0.30,
            "prob_away": 0.30,
            "prob_over25": 0.50,
            "prob_btts": 0.50,
            "confidence": "baja",
            "model_variant": "base",
        }
    ]
    matches_with_odds = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "odd_home": 2.50,
            "odd_draw": 3.30,
            "odd_away": 3.00,
            "odd_over25": 2.00,
            "odd_under25": 1.85,
        }
    ]
    picks = generate_picks(predictions, matches_with_odds)
    assert len(picks) == 0


def test_generate_picks_skips_missing_odds():
    predictions = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "prob_home": 0.55,
            "prob_draw": 0.25,
            "prob_away": 0.20,
            "prob_over25": 0.65,
            "prob_btts": 0.50,
            "confidence": "alta",
            "model_variant": "premium",
        }
    ]
    matches_with_odds = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "odd_home": None,
            "odd_draw": None,
            "odd_away": None,
            "odd_over25": None,
            "odd_under25": None,
        }
    ]
    picks = generate_picks(predictions, matches_with_odds)
    assert len(picks) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_value.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.betting'`

- [ ] **Step 3: Create package init**

Create empty `backend/betting/__init__.py`.

- [ ] **Step 4: Implement `backend/betting/value.py`**

```python
import logging

logger = logging.getLogger(__name__)

MIN_EDGE = 0.05


def calculate_edge(model_prob: float, odd: float) -> dict:
    implied_prob = 1 / odd
    edge = model_prob - implied_prob
    expected_value = (model_prob * odd) - 1
    return {
        "implied_prob": round(implied_prob, 4),
        "edge": round(edge, 4),
        "expected_value": round(expected_value, 4),
    }


def classify_stake(edge: float, confidence: str) -> int:
    if edge > 0.10 and confidence == "alta":
        return 3
    if edge > 0.07 and confidence in ("alta", "media"):
        return 2
    if edge > MIN_EDGE:
        return 1
    return 0


def generate_picks(predictions: list[dict], matches_with_odds: list[dict]) -> list[dict]:
    odds_lookup: dict[tuple, dict] = {}
    for m in matches_with_odds:
        key = (m["match_date"], m["home_team"], m["away_team"])
        odds_lookup[key] = m

    picks = []
    for pred in predictions:
        key = (pred["match_date"], pred["home_team"], pred["away_team"])
        odds = odds_lookup.get(key)
        if not odds:
            continue

        candidates = []

        if odds.get("odd_home"):
            candidates.append(("1x2_home", "H", pred["prob_home"], odds["odd_home"]))
        if odds.get("odd_draw"):
            candidates.append(("1x2_draw", "D", pred["prob_draw"], odds["odd_draw"]))
        if odds.get("odd_away"):
            candidates.append(("1x2_away", "A", pred["prob_away"], odds["odd_away"]))
        if odds.get("odd_over25"):
            candidates.append(("over25", "Over", pred["prob_over25"], odds["odd_over25"]))
        if odds.get("odd_under25"):
            prob_under = 1 - pred["prob_over25"] if pred.get("prob_over25") else None
            if prob_under is not None:
                candidates.append(("under25", "Under", prob_under, odds["odd_under25"]))

        for market, selection, model_prob, odd in candidates:
            if model_prob is None or odd is None:
                continue

            calc = calculate_edge(model_prob, odd)
            stake = classify_stake(calc["edge"], pred.get("confidence", "baja"))
            if stake == 0:
                continue

            picks.append({
                "match_date": pred["match_date"],
                "home_team": pred["home_team"],
                "away_team": pred["away_team"],
                "division": pred["division"],
                "market": market,
                "selection": selection,
                "model_prob": round(model_prob, 4),
                "implied_prob": calc["implied_prob"],
                "edge": calc["edge"],
                "odd": odd,
                "bookmaker": odds.get("bookmaker_h2h") if market.startswith("1x2") else odds.get("bookmaker_totals"),
                "stake": stake,
                "expected_value": calc["expected_value"],
                "confidence": pred.get("confidence", "baja"),
                "model_variant": pred.get("model_variant", "base"),
            })

    logger.info("Generated %d picks from %d predictions", len(picks), len(predictions))
    return picks
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_value.py -v`
Expected: All 10 tests PASS

- [ ] **Step 6: Run ruff**

Run: `PYTHONPATH=. python3 -m ruff check backend/betting/value.py tests/test_value.py`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add backend/betting/__init__.py backend/betting/value.py tests/test_value.py
git commit -m "feat: add value bet engine with edge calculation and pick generation"
```

---

### Task 4: Performance Tracker — `backend/betting/tracker.py`

**Files:**
- Create: `backend/betting/tracker.py`
- Create: `tests/test_tracker.py`

- [ ] **Step 1: Write tests for tracker**

Create `tests/test_tracker.py`:

```python
from backend.betting.tracker import (
    calculate_performance,
    resolve_single_pick,
)


def test_resolve_1x2_home_win():
    pick = {"market": "1x2_home", "selection": "H", "odd": 2.10, "stake": 2}
    match = {"ft_result": "H", "ft_home_goals": 2, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 2 * (2.10 - 1)


def test_resolve_1x2_home_loss():
    pick = {"market": "1x2_home", "selection": "H", "odd": 2.10, "stake": 2}
    match = {"ft_result": "D", "ft_home_goals": 1, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "loss"
    assert result["profit"] == -2


def test_resolve_1x2_draw_win():
    pick = {"market": "1x2_draw", "selection": "D", "odd": 3.50, "stake": 1}
    match = {"ft_result": "D", "ft_home_goals": 0, "ft_away_goals": 0}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 1 * (3.50 - 1)


def test_resolve_1x2_away_win():
    pick = {"market": "1x2_away", "selection": "A", "odd": 4.00, "stake": 1}
    match = {"ft_result": "A", "ft_home_goals": 0, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 1 * (4.00 - 1)


def test_resolve_over25_win():
    pick = {"market": "over25", "selection": "Over", "odd": 1.90, "stake": 3}
    match = {"ft_result": "H", "ft_home_goals": 2, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 3 * (1.90 - 1)


def test_resolve_over25_loss():
    pick = {"market": "over25", "selection": "Over", "odd": 1.90, "stake": 2}
    match = {"ft_result": "D", "ft_home_goals": 1, "ft_away_goals": 0}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "loss"
    assert result["profit"] == -2


def test_resolve_under25_win():
    pick = {"market": "under25", "selection": "Under", "odd": 2.00, "stake": 1}
    match = {"ft_result": "D", "ft_home_goals": 1, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 1 * (2.00 - 1)


def test_resolve_under25_loss():
    pick = {"market": "under25", "selection": "Under", "odd": 2.00, "stake": 1}
    match = {"ft_result": "H", "ft_home_goals": 2, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "loss"
    assert result["profit"] == -1


def test_calculate_performance_basic():
    resolved = [
        {"result": "win", "profit": 2.2, "stake": 2, "market": "1x2_home"},
        {"result": "loss", "profit": -1, "stake": 1, "market": "1x2_draw"},
        {"result": "win", "profit": 0.9, "stake": 1, "market": "over25"},
    ]
    perf = calculate_performance(resolved)
    assert perf["total_picks"] == 3
    assert perf["wins"] == 2
    assert perf["losses"] == 1
    assert round(perf["profit"], 2) == 2.10
    assert round(perf["roi"], 2) == round(2.10 / 4 * 100, 2)
    assert round(perf["hit_rate"], 4) == round(2 / 3, 4)


def test_calculate_performance_empty():
    perf = calculate_performance([])
    assert perf["total_picks"] == 0
    assert perf["profit"] == 0
    assert perf["roi"] == 0
    assert perf["hit_rate"] == 0


def test_calculate_performance_by_market():
    resolved = [
        {"result": "win", "profit": 2.2, "stake": 2, "market": "1x2_home"},
        {"result": "loss", "profit": -1, "stake": 1, "market": "over25"},
    ]
    perf = calculate_performance(resolved)
    assert "1x2" in perf["by_market"]
    assert "over_under" in perf["by_market"]
    assert perf["by_market"]["1x2"]["picks"] == 1
    assert perf["by_market"]["over_under"]["picks"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_tracker.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_single_pick'`

- [ ] **Step 3: Implement `backend/betting/tracker.py`**

```python
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def resolve_single_pick(pick: dict, match: dict) -> dict:
    market = pick["market"]
    selection = pick["selection"]
    odd = pick["odd"]
    stake = pick["stake"]

    won = False
    if market.startswith("1x2"):
        won = selection == match["ft_result"]
    elif market == "over25":
        total = match["ft_home_goals"] + match["ft_away_goals"]
        won = total > 2.5
    elif market == "under25":
        total = match["ft_home_goals"] + match["ft_away_goals"]
        won = total <= 2.5

    result = "win" if won else "loss"
    profit = round(stake * (odd - 1), 2) if won else -stake

    return {"result": result, "profit": profit}


def resolve_picks() -> int:
    from backend.db.client import get_supabase

    client = get_supabase()

    pending = (
        client.table("value_bets")
        .select("*")
        .is_("result", "null")
        .execute()
    )

    if not pending.data:
        logger.info("No pending picks to resolve")
        return 0

    resolved_count = 0
    for pick in pending.data:
        match_resp = (
            client.table("matches")
            .select("ft_result, ft_home_goals, ft_away_goals")
            .eq("division", pick["division"])
            .eq("match_date", pick["match_date"])
            .eq("home_team", pick["home_team"])
            .eq("away_team", pick["away_team"])
            .not_.is_("ft_result", "null")
            .execute()
        )

        if not match_resp.data:
            continue

        match = match_resp.data[0]
        resolution = resolve_single_pick(pick, match)

        client.table("value_bets").update({
            "result": resolution["result"],
            "profit": resolution["profit"],
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pick["id"]).execute()

        resolved_count += 1
        logger.info(
            "Resolved: %s vs %s [%s] → %s (%.2f u)",
            pick["home_team"],
            pick["away_team"],
            pick["selection"],
            resolution["result"],
            resolution["profit"],
        )

    logger.info("Resolved %d picks", resolved_count)
    return resolved_count


def calculate_performance(resolved: list[dict]) -> dict:
    if not resolved:
        return {
            "total_picks": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0,
            "roi": 0,
            "hit_rate": 0,
            "by_market": {},
        }

    wins = sum(1 for r in resolved if r["result"] == "win")
    losses = sum(1 for r in resolved if r["result"] == "loss")
    total_profit = sum(r["profit"] for r in resolved)
    total_stake = sum(r["stake"] for r in resolved)

    market_groups: dict[str, list[dict]] = {}
    for r in resolved:
        market = r["market"]
        group = "1x2" if market.startswith("1x2") else "over_under"
        market_groups.setdefault(group, []).append(r)

    by_market = {}
    for group, items in market_groups.items():
        g_wins = sum(1 for i in items if i["result"] == "win")
        g_stake = sum(i["stake"] for i in items)
        g_profit = sum(i["profit"] for i in items)
        by_market[group] = {
            "picks": len(items),
            "wins": g_wins,
            "profit": round(g_profit, 2),
            "roi": round(g_profit / g_stake * 100, 2) if g_stake else 0,
        }

    return {
        "total_picks": len(resolved),
        "wins": wins,
        "losses": losses,
        "profit": round(total_profit, 2),
        "roi": round(total_profit / total_stake * 100, 2) if total_stake else 0,
        "hit_rate": round(wins / len(resolved), 4),
        "by_market": by_market,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_tracker.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Run ruff**

Run: `PYTHONPATH=. python3 -m ruff check backend/betting/tracker.py tests/test_tracker.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add backend/betting/tracker.py tests/test_tracker.py
git commit -m "feat: add performance tracker with pick resolution and metrics"
```

---

### Task 5: CLI Scripts

**Files:**
- Create: `scripts/run_odds.py`
- Create: `scripts/run_value_bets.py`
- Create: `scripts/run_resolve_picks.py`

- [ ] **Step 1: Create `scripts/run_odds.py`**

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from backend.etl.odds import run_odds_sync

    result = run_odds_sync()
    logger.info("Odds sync complete: %s", result)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `scripts/run_value_bets.py`**

```python
import logging

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from backend.betting.value import generate_picks
    from backend.db.client import get_supabase

    client = get_supabase()

    logger.info("Loading predictions...")
    pred_resp = client.table("predictions").select("*").execute()
    predictions = pred_resp.data
    if not predictions:
        logger.info("No predictions found.")
        return

    logger.info("Loading matches with odds (pending results)...")
    matches_resp = (
        client.table("matches")
        .select("match_date, home_team, away_team, division, odd_home, odd_draw, odd_away, odd_over25, odd_under25")
        .is_("ft_result", "null")
        .not_.is_("odd_home", "null")
        .execute()
    )
    matches_with_odds = matches_resp.data
    if not matches_with_odds:
        logger.info("No matches with odds found.")
        return

    logger.info("Generating picks from %d predictions and %d matches with odds...",
                len(predictions), len(matches_with_odds))
    picks = generate_picks(predictions, matches_with_odds)

    if not picks:
        logger.info("No value bets found.")
        return

    logger.info("Uploading %d picks to value_bets...", len(picks))
    for pick in picks:
        client.table("value_bets").upsert(
            pick, on_conflict="match_date,home_team,away_team,market"
        ).execute()

    logger.info("Done! %d value bets uploaded.", len(picks))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `scripts/run_resolve_picks.py`**

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from backend.betting.tracker import resolve_picks

    resolved = resolve_picks()
    logger.info("Resolved %d picks", resolved)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Commit**

```bash
git add scripts/run_odds.py scripts/run_value_bets.py scripts/run_resolve_picks.py
git commit -m "feat: add CLI scripts for odds, value bets, and pick resolution"
```

---

### Task 6: Dashboard Components — `value_bets.py` and `performance.py`

**Files:**
- Create: `dashboard/components/value_bets.py`
- Create: `dashboard/components/performance.py`

- [ ] **Step 1: Create `dashboard/components/value_bets.py`**

```python
import pandas as pd


def _stake_badge(stake: int) -> str:
    if stake == 3:
        return "🟢🟢🟢 3u"
    if stake == 2:
        return "🟢🟢 2u"
    return "⚪ 1u"


def _market_label(market: str) -> str:
    labels = {
        "1x2_home": "Local",
        "1x2_draw": "Empate",
        "1x2_away": "Visitante",
        "over25": "Over 2.5",
        "under25": "Under 2.5",
    }
    return labels.get(market, market)


def _result_badge(result: str) -> str:
    if result == "win":
        return "✅ Ganado"
    if result == "loss":
        return "❌ Perdido"
    return "⏳ Pendiente"


def format_picks(picks: list[dict]) -> pd.DataFrame:
    if not picks:
        return pd.DataFrame()

    df = pd.DataFrame(picks)
    display = pd.DataFrame({
        "Fecha": df["match_date"],
        "Partido": df["home_team"] + " vs " + df["away_team"],
        "Liga": df["division"],
        "Pick": df["market"].apply(_market_label),
        "Cuota": df["odd"].apply(lambda x: f"{x:.2f}"),
        "Edge": df["edge"].apply(lambda x: f"{x:.1%}"),
        "Stake": df["stake"].apply(_stake_badge),
        "EV": df["expected_value"].apply(lambda x: f"{x:.1%}"),
    })
    return display


def format_resolved(picks: list[dict]) -> pd.DataFrame:
    if not picks:
        return pd.DataFrame()

    df = pd.DataFrame(picks)
    display = pd.DataFrame({
        "Fecha": df["match_date"],
        "Partido": df["home_team"] + " vs " + df["away_team"],
        "Pick": df["market"].apply(_market_label),
        "Cuota": df["odd"].apply(lambda x: f"{x:.2f}"),
        "Stake": df["stake"].apply(_stake_badge),
        "Resultado": df["result"].apply(_result_badge),
        "Profit": df["profit"].apply(lambda x: f"{x:+.2f}u"),
    })
    return display
```

- [ ] **Step 2: Create `dashboard/components/performance.py`**

```python
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def performance_kpis(perf: dict, prev_profit: float = 0) -> None:
    c1, c2, c3, c4 = st.columns(4)
    delta_profit = perf["profit"] - prev_profit if prev_profit else None
    c1.metric("Profit Total", f"{perf['profit']:+.2f}u", delta=f"{delta_profit:+.2f}u" if delta_profit is not None else None)
    c2.metric("ROI", f"{perf['roi']:.1f}%")
    c3.metric("Tasa de Acierto", f"{perf['hit_rate']:.1%}")
    c4.metric("Picks Resueltos", perf["total_picks"])


def market_breakdown_table(perf: dict) -> pd.DataFrame:
    rows = []
    market_labels = {"1x2": "1X2", "over_under": "Over/Under"}
    for group, data in perf.get("by_market", {}).items():
        rows.append({
            "Mercado": market_labels.get(group, group),
            "Picks": data["picks"],
            "Ganados": data["wins"],
            "ROI": f"{data['roi']:.1f}%",
        })
    return pd.DataFrame(rows)


def profit_chart(resolved: list[dict]) -> go.Figure | None:
    if not resolved:
        return None

    df = pd.DataFrame(resolved)
    df = df.sort_values("match_date")
    df["cumulative_profit"] = df["profit"].cumsum()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["match_date"],
            y=df["cumulative_profit"],
            mode="lines+markers",
            line={"color": "#2ecc71", "width": 2},
            marker={"size": 6},
            name="Profit acumulado",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        title="Profit Acumulado (unidades)",
        xaxis_title="Fecha",
        yaxis_title="Profit (u)",
        template="plotly_dark",
        height=400,
    )
    return fig
```

- [ ] **Step 3: Run ruff**

Run: `PYTHONPATH=. python3 -m ruff check dashboard/components/value_bets.py dashboard/components/performance.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/value_bets.py dashboard/components/performance.py
git commit -m "feat: add dashboard components for value bets and performance"
```

---

### Task 7: Dashboard Page — `5_value_bets.py`

**Files:**
- Create: `dashboard/pages/5_value_bets.py`

- [ ] **Step 1: Create the Streamlit page**

```python
import pandas as pd
import streamlit as st

from backend.betting.tracker import calculate_performance
from dashboard.components.performance import (
    market_breakdown_table,
    performance_kpis,
    profit_chart,
)
from dashboard.components.value_bets import format_picks, format_resolved
from dashboard.data_access import DIVISION_NAMES, get_supabase_client

st.set_page_config(page_title="Value Bets", layout="wide")
st.title("Value Bets")

client = get_supabase_client()

# --- Section 1: Picks del Dia ---
st.header("Picks del Dia")

col1, col2 = st.columns(2)
with col1:
    leagues = ["Todas"] + list(DIVISION_NAMES.keys())
    league_filter = st.selectbox(
        "Liga",
        leagues,
        format_func=lambda x: "Todas las ligas" if x == "Todas" else DIVISION_NAMES.get(x, x),
    )
with col2:
    stake_filter = st.selectbox("Stake minimo", ["Todos", "≥2u", "3u"])

try:
    query = (
        client.table("value_bets")
        .select("*")
        .is_("result", "null")
        .order("match_date")
    )
    if league_filter != "Todas":
        query = query.eq("division", league_filter)
    resp = query.execute()
    active_picks = resp.data or []
except Exception:
    active_picks = []

if stake_filter == "≥2u":
    active_picks = [p for p in active_picks if p["stake"] >= 2]
elif stake_filter == "3u":
    active_picks = [p for p in active_picks if p["stake"] == 3]

if active_picks:
    active_picks.sort(key=lambda p: (-p["edge"], p["match_date"]))
    display = format_picks(active_picks)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption(f"{len(active_picks)} picks activos")
else:
    st.info("No hay picks con valor para los proximos partidos")

# --- Section 2: Rendimiento Historico ---
st.header("Rendimiento Historico")

try:
    resolved_resp = (
        client.table("value_bets")
        .select("*")
        .not_.is_("result", "null")
        .order("match_date", desc=True)
        .execute()
    )
    resolved_picks = resolved_resp.data or []
except Exception:
    resolved_picks = []

if resolved_picks:
    perf = calculate_performance(resolved_picks)
    performance_kpis(perf)

    st.subheader("Desglose por Mercado")
    breakdown = market_breakdown_table(perf)
    if not breakdown.empty:
        st.dataframe(breakdown, use_container_width=True, hide_index=True)

    st.subheader("Profit Acumulado")
    chart = profit_chart(resolved_picks)
    if chart:
        st.plotly_chart(chart, use_container_width=True)

    st.subheader("Ultimos 20 Picks Resueltos")
    recent = resolved_picks[:20]
    resolved_display = format_resolved(recent)
    if not resolved_display.empty:
        st.dataframe(resolved_display, use_container_width=True, hide_index=True)
else:
    st.info("No hay picks resueltos aun. Los picks se resuelven automaticamente cuando los resultados estan disponibles.")
```

- [ ] **Step 2: Run ruff**

Run: `PYTHONPATH=. python3 -m ruff check dashboard/pages/5_value_bets.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add dashboard/pages/5_value_bets.py
git commit -m "feat: add Value Bets dashboard page"
```

---

### Task 8: ETL Pipeline Update

**Files:**
- Modify: `.github/workflows/etl.yml`

- [ ] **Step 1: Add 3 new steps to the ETL workflow**

After the existing "Generate predictions for upcoming matches" step and before "Commit models and backtest results", add these 3 steps:

```yaml
      - name: Fetch current odds
        run: PYTHONPATH=. python scripts/run_odds.py
        env:
          ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Generate value bets
        run: PYTHONPATH=. python scripts/run_value_bets.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Resolve past picks
        run: PYTHONPATH=. python scripts/run_resolve_picks.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

The complete pipeline order after this change:

1. Checkout + setup Python + install deps
2. `run_etl.py` — download match CSVs
3. `run_understat.py --current` — xG scraping
4. `run_fixtures.py` — upcoming fixtures
5. `run_features.py` — compute features
6. Commit features
7. `run_training.py` — train models + backtest
8. `run_predictions.py --upcoming` — predictions
9. `run_odds.py` — **odds from The Odds API** (NEW)
10. `run_value_bets.py` — **generate picks** (NEW)
11. `run_resolve_picks.py` — **resolve past picks** (NEW)
12. Commit models + backtest results

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/etl.yml
git commit -m "feat: add odds, value bets, and pick resolution to ETL pipeline"
```

---

### Task 9: Integration Verification

- [ ] **Step 1: Run the full test suite**

Run: `PYTHONPATH=. python3 -m pytest tests/ -v`
Expected: All tests pass (existing + 26 new tests from test_odds.py, test_value.py, test_tracker.py)

- [ ] **Step 2: Run ruff on all new files**

Run: `PYTHONPATH=. python3 -m ruff check backend/etl/odds.py backend/betting/ scripts/run_odds.py scripts/run_value_bets.py scripts/run_resolve_picks.py dashboard/components/value_bets.py dashboard/components/performance.py dashboard/pages/5_value_bets.py`
Expected: No errors

- [ ] **Step 3: Verify Streamlit page loads**

Run: `PYTHONPATH=. python3 -m streamlit run dashboard/app.py`
Navigate to the "Value Bets" page in the sidebar. Expected: page loads without errors, shows "No hay picks con valor" and "No hay picks resueltos" messages (since no data exists yet).

- [ ] **Step 4: Verify GitHub Actions workflow YAML is valid**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/etl.yml')); print('Valid YAML')"` (requires PyYAML — if not available, visually inspect the file)

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add -A
git diff --cached --quiet || git commit -m "fix: integration fixes for Phase 4"
```

---

### Manual Steps (Post-Implementation)

These steps require human action outside the codebase:

1. **Create `value_bets` table in Supabase:** Run `backend/db/schema_value_bets.sql` in the Supabase SQL editor
2. **Register for The Odds API:** Go to https://the-odds-api.com, create account, get API key
3. **Add `ODDS_API_KEY` to GitHub Actions secrets:** `gh secret set ODDS_API_KEY`
4. **Test the pipeline end-to-end:** Trigger the ETL workflow manually via `gh workflow run etl.yml`
