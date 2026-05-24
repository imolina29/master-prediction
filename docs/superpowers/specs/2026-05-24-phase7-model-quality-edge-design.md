# Phase 7: Model Quality & Edge Measurement — Design Spec

## Goal

Improve the predictive quality of Master Prediction's models and fix how edge is measured, moving from negative ROI (-4.9% base, -4.0% premium) toward breakeven or positive through: correcting the edge calculation, adding high-impact features, optimizing training cadence, improving backtesting rigor, and exposing performance segmentation in the dashboard.

## Architecture

Bottom-up approach: fix measurement first (vig removal, backtest improvements), then optimize (weekly training, new features), then expose (dashboard segmentation). Each layer builds on the previous — measuring correctly before optimizing ensures changes are validated accurately.

All changes stay within the existing Python stack. No new dependencies, no new tables, no new API integrations.

## Tech Stack

- Python 3.13 (local) / 3.12 (CI)
- XGBoost, scikit-learn, pandas, numpy
- Supabase (PostgreSQL free tier) — no schema changes
- Streamlit dashboard
- GitHub Actions workflows

---

## 1. Vig Removal (Edge Calculation Fix)

### Problem

`backend/betting/value.py:calculate_edge()` computes `implied_prob = 1/odd`, but bookmaker odds include a margin (vig) of ~5-8%. This overestimates the market's implied probability, making our measured edge smaller than it really is.

Example: odds Home 2.10, Draw 3.50, Away 4.50 produce raw implied probs summing to 1.06, not 1.00. The 6% excess is the bookmaker margin.

### Solution

Multiplicative (proportional) vig removal:

```python
raw_probs = [1/odd_home, 1/odd_draw, 1/odd_away]
overround = sum(raw_probs)
fair_probs = [p / overround for p in raw_probs]
```

For binary markets (over/under 2.5):

```python
raw_probs = [1/odd_over, 1/odd_under]
overround = sum(raw_probs)
fair_probs = [p / overround for p in raw_probs]
```

### Files Modified

- **`backend/betting/value.py`**:
  - New function `remove_vig(odds: list[float]) -> list[float]` — takes all market odds, returns fair probabilities.
  - `calculate_edge()` signature changes: receives `market_odds: list[float]` (all odds for the market) and `selection_index: int` (which outcome to evaluate) instead of a single `odd`.
  - `generate_picks()` passes all market odds to `calculate_edge()`.
  - Fallback: if market odds aren't available, use `1/odd` as before.

- **`backend/ml/evaluate.py`**:
  - `simulate_roi()` uses `remove_vig()` for computing implied probability instead of `1/odd_val`.

- **`dashboard/views/5_value_bets.py`**:
  - Update calls to `calculate_edge()` to pass market odds.

- **`tests/test_value.py`**:
  - Update all tests to pass market odds.
  - New tests for `remove_vig()`.

### Expected Impact

Edge values increase by ~3-5 percentage points. Some picks previously below MIN_EDGE (0.08) may now qualify. Backtesting ROI should improve by 2-4 percentage points.

---

## 2. Backtest Improvements (Bankroll Simulation)

### Problem

`simulate_roi()` returns only `roi_pct` and `n_bets`. This hides risk — a +5% ROI with -40u max drawdown is not viable.

### New Metrics

Added to `simulate_roi()` return dict:

| Metric | Description |
|--------|-------------|
| `max_drawdown` | Largest peak-to-trough decline in cumulative profit (units) |
| `max_losing_streak` | Longest consecutive losing run |
| `profit_curve` | List of cumulative profit after each bet (for charting) |
| `kelly_roi_pct` | ROI using fractional Kelly staking (25%) as comparison |

### Kelly Fraccional (Reference Only)

```python
kelly_fraction = 0.25 * (edge / (odd - 1))
stake = bankroll * kelly_fraction  # bankroll starts at 100u
```

This does NOT change the live staking system (1-3u stays). It provides a reference point in backtesting to show what optimized sizing would yield.

### Files Modified

- **`backend/ml/evaluate.py`**:
  - `simulate_roi()` extended with new metrics in return dict.
  - New helper `_compute_drawdown(profit_curve: list[float]) -> float`.
  - New helper `_compute_max_streak(results: list[bool], target: bool) -> int`.
  - Kelly simulation runs in parallel within the same loop.

- **`data/backtest_results.json`**:
  - Each fold gains: `max_drawdown`, `max_losing_streak`, `kelly_roi_pct`, `profit_curve`.
  - Summary level gains: `mean_max_drawdown`, `mean_max_losing_streak`, `mean_kelly_roi_pct`.

- **`tests/test_ml_evaluate.py`**:
  - Tests for drawdown, streak, and Kelly calculations.

### What We Don't Do

- No Monte Carlo simulation (insufficient volume for statistical significance).
- No changes to live staking logic.

---

## 3. Weekly Training

### Problem

The ETL pipeline trains 6 models + runs backtesting every day. With ~100K matches and only 1-2 new results daily, this introduces prediction variance without meaningful model improvement and wastes ~15-20 min of CI compute.

### Solution

Split training into a separate weekly workflow.

### New Workflow: `.github/workflows/training.yml`

- **Schedule:** `cron: "0 10 * * 1"` — Monday 10:00 UTC (5:00 AM Colombia)
- **Why Monday:** European leagues finish their matchday Sunday night. Monday morning has all weekend results available.
- **Why 10:00 UTC:** Runs before the daily ETL at 12:00 UTC, so Monday predictions use fresh models.
- **Steps:** checkout → install deps → run features → train 6 models → backtesting → commit models + backtest results → Telegram summary notification

### Modified Workflow: `.github/workflows/etl.yml`

- **Remove** the "Train models and run backtesting" step.
- **Remove** the "Commit backtest results" step.
- Predictions continue using existing `.joblib` models via `_load_model()` — no code changes needed.

### Telegram Training Summary

After training completes, send a Telegram message:

```
📊 Modelos re-entrenados

base_1x2: acc 48.3% | ROI -4.9%
premium_1x2: acc 52.5% | ROI -4.0%
base_over25: acc 55.9%
premium_over25: acc 56.1%
base_btts: acc 53.3%
premium_btts: acc 54.9%
```

### Files Modified

- **Create** `.github/workflows/training.yml`
- **Modify** `.github/workflows/etl.yml` — remove training steps
- **Create** `scripts/run_training_notify.py` — wraps `run_training.py` + sends Telegram summary
- **`backend/notifications/telegram.py`** — new `send_training_summary(results: dict)` method

### What We Don't Do

- No model versioning or A/B testing.
- No conditional training ("only train if N new matches").

---

## 4. New Features

### 4.1 Rest Days

**Features:** `home_rest_days`, `away_rest_days`

**Calculation:** For each team-match row in `_expand_to_team_rows()`, compute days since the team's previous match by diffing `match_date` with the previous row's `match_date` (grouped by team, sorted by date).

**Default:** 7 days when no previous match exists.

**Signal:** Fixture congestion (3 days rest) is a strong negative predictor, especially for teams in European competitions playing midweek.

### 4.2 League Position

**Features:** `home_league_pos`, `away_league_pos`, `league_pos_diff`

**Calculation:** Cumulative points per team within each `(division, season)` group. Points: 3 for win, 1 for draw, 0 for loss. Rank within the division at each match date. Normalize to [0, 1] range by dividing position by number of teams (0.0 = leader, 1.0 = last).

**Season detection:** Derived from `match_date` — matches from August to May belong to one season. Boundary: July 1st (consistent with existing `SEASON_BOUNDARIES` in config).

**Note:** This is a proxy for actual league standings, not the official table. It captures the same signal without needing an external standings API.

### 4.3 H2H (Head-to-Head)

**Features:** `h2h_home_win_rate`, `h2h_avg_goals`, `h2h_matches`

**Calculation:** For each match, look up all prior matches between the same two teams (any venue). Compute:
- `h2h_home_win_rate`: percentage of times the home team won against this specific opponent (home or away)
- `h2h_avg_goals`: average total goals in prior H2H meetings
- `h2h_matches`: count of prior meetings (capped signal — diminishing returns past 10)

**Defaults:** 0.5 for win_rate, global average goals for avg_goals, 0 for matches (when teams have never met).

**Existing code:** `compute_h2h_features()` in `backend/services/features.py` already does this for the dashboard. The model feature version is computed vectorized during `compute_team_features()` instead of per-pair lookups.

### 4.4 Venue Splits

**Features:** `home_venue_win_rate`, `home_venue_goals_avg`, `away_venue_win_rate`, `away_venue_goals_avg`

**Calculation:** Rolling window of 5 matches filtered by venue. For the home team, only consider matches played at home. For the away team, only consider matches played away. Uses the same `shift(1).rolling(5, min_periods=1).mean()` pattern as existing features.

**Signal:** Some teams are dominant at home but weak away (or vice versa). Current rolling stats mix both venues, diluting this signal.

### Integration into Model Config

**`backend/ml/config.py`:**

New feature groups:

```python
_MATCHDAY = ["home_rest_days", "away_rest_days"]

_STANDINGS = ["home_league_pos", "away_league_pos", "league_pos_diff"]

_H2H = ["h2h_home_win_rate", "h2h_avg_goals", "h2h_matches"]

_VENUE = [
    "home_venue_win_rate", "home_venue_goals_avg",
    "away_venue_win_rate", "away_venue_goals_avg",
]
```

Both `BASE_FEATURES` and `PREMIUM_FEATURES` gain all 13 new features:
- BASE: 31 → 44 features
- PREMIUM: 39 → 52 features

### Files Modified

- **`backend/services/features.py`**:
  - `compute_team_features()` gains rest days, venue splits as new columns.
  - New helper `_compute_league_position(df)` for standings proxy.
  - New helper `_compute_h2h_features(df)` for vectorized H2H (adapts existing `compute_h2h_features`).

- **`backend/ml/features.py`**:
  - `build_match_features()` merges the new columns with correct home/away prefixes.

- **`backend/ml/config.py`**:
  - New feature lists added to `BASE_FEATURES` and `PREMIUM_FEATURES`.

- **`tests/test_features.py`** and **`tests/test_ml_features.py`**:
  - Tests for rest days, league position, H2H, venue splits.

### What We Don't Do

- No referee features (not available in football-data.org free CSV).
- No CLV tracking (requires historical closing odds from paid API tier).
- No weather features (low signal-to-noise for the effort).

---

## 5. Dashboard — Segmented Performance

### Change

Add filters to the "Rendimiento Historico" section of `dashboard/views/5_value_bets.py`. KPIs, market breakdown, and profit chart recalculate based on selected filters.

### Filters

Row of 4 selectboxes above the performance KPIs:

| Filter | Options | Default |
|--------|---------|---------|
| Liga | Todas, E0, SP1, D1, I1, F1 | Todas |
| Mercado | Todos, 1X2, Over/Under | Todos |
| Confianza | Todas, Alta, Media, Baja | Todas |
| Modelo | Todos, Base, Premium | Todos |

### Logic

Filter `resolved_picks` list in-memory before passing to `calculate_performance()`. No new Supabase queries — `get_resolved_picks()` already returns all fields needed for filtering (`division`, `market`, `confidence`, `model_variant`).

Market filter maps: "1X2" matches `market.startswith("1x2")`, "Over/Under" matches `market in ("over25", "under25")`.

### Files Modified

- **`dashboard/views/5_value_bets.py`**:
  - Add filter selectboxes.
  - Apply filters to `resolved_picks` before `calculate_performance()`.

### What We Don't Do

- No new page.
- No heatmaps or cross-dimensional comparisons.
- No temporal filter (profit chart already shows time progression).

---

## Implementation Order

1. **Vig removal** — Fix measurement foundation
2. **Backtest improvements** — Better evaluation metrics
3. **Weekly training** — Reduce noise, separate concerns
4. **New features** — Improve model quality (rest days → league position → H2H → venue splits)
5. **Dashboard segmentation** — Expose insights

Each step is independently deployable and testable. After steps 1-2, re-run backtesting to establish the corrected baseline before adding features in step 4.

## Success Criteria

- Backtesting ROI improves (less negative or positive) after vig correction
- New features show positive feature importance in at least 2 of 6 models
- Max drawdown is tracked and visible in backtest results
- Training runs weekly without affecting daily predictions
- Dashboard allows filtering performance by liga, mercado, confianza, modelo
