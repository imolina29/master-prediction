# Phase 7: Model Quality & Edge Measurement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix edge measurement (vig removal), improve backtesting rigor, separate training to weekly, add 15 high-impact features (rest days, league position, H2H, venue splits), and segment performance in the dashboard.

**Architecture:** Bottom-up: fix measurement (Tasks 1-2), optimize pipeline (Task 3), improve models (Tasks 4-7), expose results (Task 8). Each task is independently deployable.

**Tech Stack:** Python 3.13/3.12, XGBoost, pandas, numpy, scikit-learn, Streamlit, GitHub Actions

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/betting/value.py` | Vig removal + edge calculation fix |
| Modify | `backend/ml/evaluate.py` | Backtest metrics: drawdown, streaks, Kelly |
| Create | `.github/workflows/training.yml` | Weekly training workflow |
| Modify | `.github/workflows/etl.yml` | Remove training steps from daily pipeline |
| Create | `scripts/run_training_notify.py` | Training wrapper with Telegram notification |
| Modify | `backend/notifications/telegram.py` | Training summary message |
| Modify | `backend/services/features.py` | Rest days, venue splits, H2H, league position |
| Modify | `backend/ml/features.py` | Merge new features into match rows |
| Modify | `backend/ml/config.py` | Register 13 new features |
| Modify | `dashboard/views/5_value_bets.py` | Performance filters + updated edge calls |
| Modify | `tests/test_value.py` | Updated tests for vig removal |
| Modify | `tests/test_ml_evaluate.py` | Tests for drawdown, streaks, Kelly |
| Modify | `tests/test_features.py` | Tests for rest days, venue, H2H, league pos |
| Modify | `tests/test_ml_features.py` | Tests for new feature columns in match rows |

---

### Task 1: Vig Removal — `remove_vig` function and `calculate_edge` update

**Files:**
- Modify: `backend/betting/value.py`
- Modify: `tests/test_value.py`

- [ ] **Step 1: Write failing tests for `remove_vig`**

Add to `tests/test_value.py`:

```python
from backend.betting.value import remove_vig


def test_remove_vig_three_way():
    # Odds: Home 2.10, Draw 3.50, Away 4.50
    # Raw implied: 1/2.10 + 1/3.50 + 1/4.50 = 0.4762 + 0.2857 + 0.2222 = 0.9841
    # Wait — these odds actually sum to < 1.0. Use realistic odds with overround:
    # Home 1.90, Draw 3.40, Away 4.20 => 0.5263 + 0.2941 + 0.2381 = 1.0585
    fair = remove_vig([1.90, 3.40, 4.20])
    assert len(fair) == 3
    assert abs(sum(fair) - 1.0) < 0.0001
    assert fair[0] > fair[1] > fair[2]


def test_remove_vig_two_way():
    # Over 1.85, Under 2.05 => 0.5405 + 0.4878 = 1.0283
    fair = remove_vig([1.85, 2.05])
    assert len(fair) == 2
    assert abs(sum(fair) - 1.0) < 0.0001
    assert fair[0] > fair[1]


def test_remove_vig_single_fallback():
    fair = remove_vig([2.50])
    assert len(fair) == 1
    assert fair[0] == 1 / 2.50
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_value.py::test_remove_vig_three_way tests/test_value.py::test_remove_vig_two_way tests/test_value.py::test_remove_vig_single_fallback -v`
Expected: FAIL with `ImportError: cannot import name 'remove_vig'`

- [ ] **Step 3: Implement `remove_vig`**

In `backend/betting/value.py`, add after the `MIN_EDGE` line:

```python
def remove_vig(odds: list[float]) -> list[float]:
    if len(odds) < 2:
        return [1 / odds[0]] if odds else []
    raw = [1 / o for o in odds]
    overround = sum(raw)
    return [p / overround for p in raw]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_value.py::test_remove_vig_three_way tests/test_value.py::test_remove_vig_two_way tests/test_value.py::test_remove_vig_single_fallback -v`
Expected: PASS

- [ ] **Step 5: Write failing tests for updated `calculate_edge`**

Replace existing `test_calculate_edge_positive` and `test_calculate_edge_negative` in `tests/test_value.py`:

```python
def test_calculate_edge_positive():
    result = calculate_edge(
        model_prob=0.55,
        selection_index=0,
        market_odds=[1.90, 3.40, 4.20],
    )
    fair = remove_vig([1.90, 3.40, 4.20])
    assert round(result["implied_prob"], 4) == round(fair[0], 4)
    assert round(result["edge"], 4) == round(0.55 - fair[0], 4)
    assert round(result["expected_value"], 4) == round((0.55 * 1.90) - 1, 4)


def test_calculate_edge_negative():
    result = calculate_edge(
        model_prob=0.30,
        selection_index=0,
        market_odds=[1.90, 3.40, 4.20],
    )
    assert result["edge"] < 0


def test_calculate_edge_fallback_single_odd():
    result = calculate_edge(model_prob=0.55, selection_index=0, market_odds=[2.10])
    assert round(result["implied_prob"], 4) == round(1 / 2.10, 4)
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_value.py::test_calculate_edge_positive tests/test_value.py::test_calculate_edge_negative tests/test_value.py::test_calculate_edge_fallback_single_odd -v`
Expected: FAIL with `TypeError` (wrong signature)

- [ ] **Step 7: Update `calculate_edge` signature**

Replace the existing `calculate_edge` function in `backend/betting/value.py`:

```python
def calculate_edge(
    model_prob: float,
    selection_index: int,
    market_odds: list[float],
) -> dict:
    fair_probs = remove_vig(market_odds)
    implied_prob = fair_probs[selection_index]
    odd = market_odds[selection_index]
    edge = model_prob - implied_prob
    expected_value = (model_prob * odd) - 1
    return {
        "implied_prob": round(implied_prob, 4),
        "edge": round(edge, 4),
        "expected_value": round(expected_value, 4),
    }
```

- [ ] **Step 8: Run updated edge tests**

Run: `PYTHONPATH=. python3 -m pytest tests/test_value.py::test_calculate_edge_positive tests/test_value.py::test_calculate_edge_negative tests/test_value.py::test_calculate_edge_fallback_single_odd -v`
Expected: PASS

- [ ] **Step 9: Update `generate_picks` to pass market odds**

Replace the `generate_picks` function in `backend/betting/value.py`. The key change is building market_odds lists and passing selection_index to `calculate_edge`:

```python
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

        h2h_odds = [
            o for o in [odds.get("odd_home"), odds.get("odd_draw"), odds.get("odd_away")]
            if o and o > 1.0
        ]
        totals_odds = [
            o for o in [odds.get("odd_over25"), odds.get("odd_under25")]
            if o and o > 1.0
        ]

        candidates = []

        if odds.get("odd_home") and odds["odd_home"] > 1.0 and len(h2h_odds) >= 2:
            idx = h2h_odds.index(odds["odd_home"])
            candidates.append(("1x2_home", "H", pred["prob_home"], odds["odd_home"], h2h_odds, idx))
        if odds.get("odd_draw") and odds["odd_draw"] > 1.0 and len(h2h_odds) >= 2:
            idx = h2h_odds.index(odds["odd_draw"])
            candidates.append(("1x2_draw", "D", pred["prob_draw"], odds["odd_draw"], h2h_odds, idx))
        if odds.get("odd_away") and odds["odd_away"] > 1.0 and len(h2h_odds) >= 2:
            idx = h2h_odds.index(odds["odd_away"])
            candidates.append(("1x2_away", "A", pred["prob_away"], odds["odd_away"], h2h_odds, idx))
        if odds.get("odd_over25") and odds["odd_over25"] > 1.0 and len(totals_odds) >= 2:
            idx = totals_odds.index(odds["odd_over25"])
            candidates.append((
                "over25", "Over", pred["prob_over25"], odds["odd_over25"], totals_odds, idx,
            ))
        if odds.get("odd_under25") and odds["odd_under25"] > 1.0 and len(totals_odds) >= 2:
            prob_under = 1 - pred["prob_over25"] if pred.get("prob_over25") else None
            if prob_under is not None:
                idx = totals_odds.index(odds["odd_under25"])
                candidates.append((
                    "under25", "Under", prob_under, odds["odd_under25"], totals_odds, idx,
                ))

        for market, selection, model_prob, odd, mkt_odds, sel_idx in candidates:
            if model_prob is None:
                continue

            calc = calculate_edge(model_prob, sel_idx, mkt_odds)
            stake = classify_stake(calc["edge"], pred.get("confidence", "baja"))
            if stake == 0:
                continue

            picks.append(
                {
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
                    "bookmaker": (
                        odds.get("bookmaker_h2h")
                        if market.startswith("1x2")
                        else odds.get("bookmaker_totals")
                    ),
                    "stake": stake,
                    "expected_value": calc["expected_value"],
                    "confidence": pred.get("confidence", "baja"),
                    "model_variant": pred.get("model_variant", "base"),
                }
            )

    logger.info("Generated %d picks from %d predictions", len(picks), len(predictions))
    return picks
```

- [ ] **Step 10: Update remaining tests in `test_value.py`**

Update `classify_stake` tests (no change needed — they don't call `calculate_edge`) and `generate_picks` tests. The `generate_picks` tests already provide full odds dicts so they work with the new code. Run all:

Run: `PYTHONPATH=. python3 -m pytest tests/test_value.py -v`
Expected: PASS (all tests)

- [ ] **Step 11: Update `simulate_roi` in evaluate.py to use `remove_vig`**

In `backend/ml/evaluate.py`, add import at top:

```python
from backend.betting.value import remove_vig
```

Replace the inner loop of `simulate_roi`:

```python
def simulate_roi(
    probs: np.ndarray,
    actuals: np.ndarray,
    odds: pd.DataFrame,
    threshold: float = 0.08,
) -> dict:
    total_bets = 0
    total_profit = 0.0

    odd_cols = ["odd_home", "odd_draw", "odd_away"]
    for i in range(len(actuals)):
        market_odds = [
            odds.iloc[i][c] for c in odd_cols
            if not pd.isna(odds.iloc[i][c]) and odds.iloc[i][c] > 1.0
        ]
        if len(market_odds) < 2:
            continue
        fair_probs = remove_vig(market_odds)

        odds_idx = 0
        for cls_idx, odd_col in enumerate(odd_cols):
            odd_val = odds.iloc[i][odd_col]
            if pd.isna(odd_val) or odd_val <= 1.0:
                continue
            implied_prob = fair_probs[odds_idx]
            model_prob = probs[i][cls_idx]
            edge = model_prob - implied_prob
            odds_idx += 1
            if edge > threshold:
                total_bets += 1
                if actuals[i] == cls_idx:
                    total_profit += odd_val - 1.0
                else:
                    total_profit -= 1.0

    roi_pct = (total_profit / total_bets * 100) if total_bets > 0 else 0.0
    return {"roi_pct": round(roi_pct, 2), "n_bets": total_bets}
```

- [ ] **Step 12: Update dashboard `5_value_bets.py` call to `calculate_edge`**

In `dashboard/views/5_value_bets.py`, update the import at line 7:

```python
from backend.betting.value import calculate_edge, remove_vig
```

Replace the edge calculation block (around lines 109-119) in the no-value-rows loop:

```python
    for pred in predictions:
        key = (pred["match_date"], pred["home_team"], pred["away_team"])
        if key in vb_keys:
            continue
        odds = matches_with_odds.get(key)
        if not odds or not odds.get("odd_home"):
            continue

        h2h_odds = [
            o for o in [odds["odd_home"], odds.get("odd_draw"), odds.get("odd_away")]
            if o and o > 1.0
        ]
        if len(h2h_odds) < 2:
            continue

        result_map = {
            "H": ("1x2_home", "H", pred["prob_home"], odds["odd_home"]),
            "D": ("1x2_draw", "D", pred["prob_draw"], odds.get("odd_draw")),
            "A": ("1x2_away", "A", pred["prob_away"], odds.get("odd_away")),
        }
        predicted = pred.get("predicted_result", "H")
        market, selection, model_prob, odd = result_map.get(predicted, result_map["H"])

        if not model_prob or not odd or odd <= 1.0:
            continue

        sel_idx = h2h_odds.index(odd) if odd in h2h_odds else 0
        calc = calculate_edge(model_prob, sel_idx, h2h_odds)
        no_value_rows.append(
            {
                "match_date": pred["match_date"],
                "home_team": pred["home_team"],
                "away_team": pred["away_team"],
                "division": pred["division"],
                "market": market,
                "selection": selection,
                "edge": calc["edge"],
                "odd": odd,
                "stake": 0,
                "expected_value": calc["expected_value"],
            }
        )
```

- [ ] **Step 13: Run all tests**

Run: `PYTHONPATH=. python3 -m pytest tests/test_value.py tests/test_ml_evaluate.py -v`
Expected: PASS

- [ ] **Step 14: Lint check**

Run: `PYTHONPATH=. python3 -m ruff check backend/betting/value.py backend/ml/evaluate.py dashboard/views/5_value_bets.py && python3 -m ruff format --check backend/betting/value.py backend/ml/evaluate.py dashboard/views/5_value_bets.py`
Expected: No errors

- [ ] **Step 15: Commit**

```bash
git add backend/betting/value.py backend/ml/evaluate.py dashboard/views/5_value_bets.py tests/test_value.py
git commit -m "feat: remove bookmaker vig from edge calculation"
```

---

### Task 2: Backtest Improvements — drawdown, streaks, Kelly

**Files:**
- Modify: `backend/ml/evaluate.py`
- Modify: `tests/test_ml_evaluate.py`

- [ ] **Step 1: Write failing tests for `_compute_drawdown` and `_compute_max_streak`**

Add to `tests/test_ml_evaluate.py`:

```python
from backend.ml.evaluate import _compute_drawdown, _compute_max_streak


def test_compute_drawdown_basic():
    # Profit curve: 1, 3, 2, 0, 4 → peak=3, trough after peak=0, drawdown=3
    curve = [1.0, 3.0, 2.0, 0.0, 4.0]
    assert _compute_drawdown(curve) == 3.0


def test_compute_drawdown_no_drawdown():
    curve = [1.0, 2.0, 3.0, 4.0]
    assert _compute_drawdown(curve) == 0.0


def test_compute_drawdown_empty():
    assert _compute_drawdown([]) == 0.0


def test_compute_max_streak_losses():
    results = [True, False, False, False, True, False]
    assert _compute_max_streak(results, target=False) == 3


def test_compute_max_streak_wins():
    results = [True, True, True, False, True, True]
    assert _compute_max_streak(results, target=True) == 3


def test_compute_max_streak_empty():
    assert _compute_max_streak([], target=False) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_ml_evaluate.py::test_compute_drawdown_basic tests/test_ml_evaluate.py::test_compute_max_streak_losses -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement `_compute_drawdown` and `_compute_max_streak`**

Add to `backend/ml/evaluate.py` after the imports:

```python
def _compute_drawdown(profit_curve: list[float]) -> float:
    if not profit_curve:
        return 0.0
    peak = profit_curve[0]
    max_dd = 0.0
    for val in profit_curve:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def _compute_max_streak(results: list[bool], target: bool) -> int:
    max_s = 0
    current = 0
    for r in results:
        if r == target:
            current += 1
            if current > max_s:
                max_s = current
        else:
            current = 0
    return max_s
```

- [ ] **Step 4: Run helper tests**

Run: `PYTHONPATH=. python3 -m pytest tests/test_ml_evaluate.py::test_compute_drawdown_basic tests/test_ml_evaluate.py::test_compute_drawdown_no_drawdown tests/test_ml_evaluate.py::test_compute_drawdown_empty tests/test_ml_evaluate.py::test_compute_max_streak_losses tests/test_ml_evaluate.py::test_compute_max_streak_wins tests/test_ml_evaluate.py::test_compute_max_streak_empty -v`
Expected: PASS

- [ ] **Step 5: Write failing test for extended `simulate_roi`**

Add to `tests/test_ml_evaluate.py`:

```python
def test_simulate_roi_extended_metrics():
    probs = np.array([[0.60, 0.20, 0.20], [0.30, 0.30, 0.40], [0.20, 0.50, 0.30]])
    actuals = np.array([0, 2, 1])
    odds = pd.DataFrame(
        {"odd_home": [2.0, 3.0, 5.0], "odd_draw": [3.5, 3.2, 2.0], "odd_away": [4.0, 2.5, 3.5]}
    )
    result = simulate_roi(probs, actuals, odds, threshold=0.05)
    assert "max_drawdown" in result
    assert "max_losing_streak" in result
    assert "profit_curve" in result
    assert "kelly_roi_pct" in result
    assert isinstance(result["max_drawdown"], float)
    assert isinstance(result["max_losing_streak"], int)
    assert isinstance(result["profit_curve"], list)
    assert isinstance(result["kelly_roi_pct"], float)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_ml_evaluate.py::test_simulate_roi_extended_metrics -v`
Expected: FAIL with `KeyError: 'max_drawdown'`

- [ ] **Step 7: Extend `simulate_roi` with new metrics**

Replace the entire `simulate_roi` function in `backend/ml/evaluate.py`:

```python
def simulate_roi(
    probs: np.ndarray,
    actuals: np.ndarray,
    odds: pd.DataFrame,
    threshold: float = 0.08,
) -> dict:
    total_bets = 0
    total_profit = 0.0
    profit_curve: list[float] = []
    bet_results: list[bool] = []

    kelly_bankroll = 100.0
    kelly_initial = kelly_bankroll

    odd_cols = ["odd_home", "odd_draw", "odd_away"]
    for i in range(len(actuals)):
        market_odds = [
            odds.iloc[i][c] for c in odd_cols
            if not pd.isna(odds.iloc[i][c]) and odds.iloc[i][c] > 1.0
        ]
        if len(market_odds) < 2:
            continue
        fair_probs = remove_vig(market_odds)

        odds_idx = 0
        for cls_idx, odd_col in enumerate(odd_cols):
            odd_val = odds.iloc[i][odd_col]
            if pd.isna(odd_val) or odd_val <= 1.0:
                continue
            implied_prob = fair_probs[odds_idx]
            model_prob = probs[i][cls_idx]
            edge = model_prob - implied_prob
            odds_idx += 1
            if edge > threshold:
                total_bets += 1
                won = actuals[i] == cls_idx
                if won:
                    total_profit += odd_val - 1.0
                else:
                    total_profit -= 1.0
                profit_curve.append(round(total_profit, 4))
                bet_results.append(won)

                kelly_f = max(0.0, 0.25 * (edge / (odd_val - 1.0)))
                kelly_stake = kelly_bankroll * kelly_f
                if won:
                    kelly_bankroll += kelly_stake * (odd_val - 1.0)
                else:
                    kelly_bankroll -= kelly_stake

    roi_pct = (total_profit / total_bets * 100) if total_bets > 0 else 0.0
    kelly_roi = ((kelly_bankroll - kelly_initial) / kelly_initial * 100) if total_bets > 0 else 0.0

    return {
        "roi_pct": round(roi_pct, 2),
        "n_bets": total_bets,
        "max_drawdown": _compute_drawdown(profit_curve),
        "max_losing_streak": _compute_max_streak(bet_results, target=False),
        "profit_curve": profit_curve,
        "kelly_roi_pct": round(kelly_roi, 2),
    }
```

- [ ] **Step 8: Run all evaluate tests**

Run: `PYTHONPATH=. python3 -m pytest tests/test_ml_evaluate.py -v`
Expected: PASS

- [ ] **Step 9: Update `walk_forward_backtest` to include summary-level metrics**

In `backend/ml/evaluate.py`, update the `result` dict computation at the end of `walk_forward_backtest` (after the folds loop):

```python
    result = {"folds": folds_results}
    if folds_results:
        result["mean_accuracy"] = round(float(np.mean([f["accuracy"] for f in folds_results])), 4)
        result["mean_log_loss"] = round(float(np.mean([f["log_loss"] for f in folds_results])), 4)
        if all("roi_pct" in f for f in folds_results):
            result["mean_roi_pct"] = round(
                float(np.mean([f["roi_pct"] for f in folds_results])), 2
            )
            result["mean_max_drawdown"] = round(
                float(np.mean([f.get("max_drawdown", 0) for f in folds_results])), 2
            )
            result["mean_max_losing_streak"] = round(
                float(np.mean([f.get("max_losing_streak", 0) for f in folds_results])), 1
            )
            result["mean_kelly_roi_pct"] = round(
                float(np.mean([f.get("kelly_roi_pct", 0) for f in folds_results])), 2
            )
```

- [ ] **Step 10: Run all tests**

Run: `PYTHONPATH=. python3 -m pytest tests/test_ml_evaluate.py tests/test_value.py -v`
Expected: PASS

- [ ] **Step 11: Lint check**

Run: `python3 -m ruff check backend/ml/evaluate.py && python3 -m ruff format --check backend/ml/evaluate.py`
Expected: No errors

- [ ] **Step 12: Commit**

```bash
git add backend/ml/evaluate.py tests/test_ml_evaluate.py
git commit -m "feat: add drawdown, losing streak, Kelly to backtesting"
```

---

### Task 3: Weekly Training — separate workflow

**Files:**
- Create: `.github/workflows/training.yml`
- Modify: `.github/workflows/etl.yml`
- Create: `scripts/run_training_notify.py`
- Modify: `backend/notifications/telegram.py`

- [ ] **Step 1: Add `send_training_summary` to `TelegramNotifier`**

Add this method to the `TelegramNotifier` class in `backend/notifications/telegram.py`:

```python
    def send_training_summary(self, results: dict) -> list[dict]:
        lines = ["📊 <b>Modelos re-entrenados</b>", ""]
        for model_name, data in results.items():
            acc = data.get("mean_accuracy", 0)
            roi = data.get("mean_roi_pct")
            dd = data.get("mean_max_drawdown")
            line = f"  {model_name}: acc <b>{acc:.1%}</b>"
            if roi is not None:
                line += f" | ROI <b>{roi:+.1f}%</b>"
            if dd is not None:
                line += f" | DD <b>{dd:.1f}u</b>"
            lines.append(line)
        return self.send_to_all("\n".join(lines), reply_markup=self._dashboard_markup())
```

- [ ] **Step 2: Create `scripts/run_training_notify.py`**

```python
import json
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from scripts.run_training import main as run_training

    run_training()

    from backend.ml.config import BACKTEST_RESULTS_PATH
    from backend.notifications.telegram import TelegramNotifier

    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.info("No TELEGRAM_BOT_TOKEN set, skipping notification")
        return

    with open(BACKTEST_RESULTS_PATH) as f:
        results = json.load(f)

    notifier = TelegramNotifier()
    notifier.send_training_summary(results)
    logger.info("Training summary sent to %d chat(s)", len(notifier.chat_ids))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `.github/workflows/training.yml`**

```yaml
name: Weekly Training

on:
  schedule:
    - cron: "0 10 * * 1"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  train-models:
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

      - name: Generate features
        run: PYTHONPATH=. python scripts/run_features.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Train models, backtest, and notify
        run: PYTHONPATH=. python scripts/run_training_notify.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          TELEGRAM_AUTHORIZED_CHATS: ${{ secrets.TELEGRAM_AUTHORIZED_CHATS }}
          DASHBOARD_URL: ${{ secrets.DASHBOARD_URL }}

      - name: Commit models and backtest results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add models/ data/backtest_results.json data/features/ -f
          git diff --cached --quiet || git commit -m "chore: weekly model retrain [skip ci]"
          git push

      - name: Notify pipeline failure via Telegram
        if: failure()
        run: |
          curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d parse_mode=HTML \
            -d text="🚨 <b>Weekly Training falló</b>%0A%0ARun: <a href='${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}'>Ver logs</a>"
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

- [ ] **Step 4: Remove training steps from `etl.yml`**

In `.github/workflows/etl.yml`, remove these two steps entirely:

1. The step `"Train models and run backtesting"` (the `run: PYTHONPATH=. python scripts/run_training.py` block with its env vars)
2. The step `"Commit backtest results"` (the `run: |` block with `git add data/backtest_results.json`)

Keep the `"Commit updated features"` step — that stays in the daily pipeline.

- [ ] **Step 5: Lint check**

Run: `python3 -m ruff check backend/notifications/telegram.py scripts/run_training_notify.py && python3 -m ruff format --check backend/notifications/telegram.py scripts/run_training_notify.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/training.yml .github/workflows/etl.yml scripts/run_training_notify.py backend/notifications/telegram.py
git commit -m "feat: separate weekly training workflow from daily ETL"
```

---

### Task 4: New Features — Rest Days

**Files:**
- Modify: `backend/services/features.py`
- Modify: `tests/test_features.py`

- [ ] **Step 1: Write failing test for rest days**

Add to `tests/test_features.py`:

```python
def test_rest_days_computed():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    assert "rest_days" in result.columns
    arsenal = result[result["team"] == "Arsenal"].sort_values("match_date")
    # First match: default 7
    assert arsenal.iloc[0]["rest_days"] == 7
    # Second match (Jan 15): 14 days after Jan 01
    assert arsenal.iloc[1]["rest_days"] == 14
    # Third match (Feb 01): 17 days after Jan 15
    assert arsenal.iloc[2]["rest_days"] == 17
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_features.py::test_rest_days_computed -v`
Expected: FAIL with `KeyError: 'rest_days'`

- [ ] **Step 3: Implement rest days in `compute_team_features`**

In `backend/services/features.py`, add at the end of `compute_team_features`, before the logger.info line:

```python
    expanded["rest_days"] = grouped["match_date"].transform(
        lambda s: s.diff().dt.days.fillna(7).astype(int)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_features.py::test_rest_days_computed -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/features.py tests/test_features.py
git commit -m "feat: add rest_days feature to team features"
```

---

### Task 5: New Features — Venue Splits

**Files:**
- Modify: `backend/services/features.py`
- Modify: `tests/test_features.py`

- [ ] **Step 1: Write failing test for venue splits**

Add to `tests/test_features.py`:

```python
def test_venue_splits_computed():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    assert "venue_win_rate" in result.columns
    assert "venue_goals_avg" in result.columns
    # All values should be floats or NaN (first match has no prior venue data)
    arsenal_home = result[
        (result["team"] == "Arsenal") & (result["venue"] == "home")
    ].sort_values("match_date")
    assert len(arsenal_home) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_features.py::test_venue_splits_computed -v`
Expected: FAIL with `KeyError: 'venue_win_rate'`

- [ ] **Step 3: Implement venue splits in `compute_team_features`**

In `backend/services/features.py`, add after the rest_days line (still inside `compute_team_features`):

```python
    venue_grouped = expanded.groupby(["team", "venue"])
    expanded["venue_win_rate"] = venue_grouped["win"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["venue_goals_avg"] = venue_grouped["goals_scored"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_features.py::test_venue_splits_computed -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/features.py tests/test_features.py
git commit -m "feat: add venue_win_rate and venue_goals_avg features"
```

---

### Task 6: New Features — League Position and H2H

**Files:**
- Modify: `backend/services/features.py`
- Modify: `tests/test_features.py`

- [ ] **Step 1: Write failing tests for league position**

Add to `tests/test_features.py`:

```python
def test_league_position_computed():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    assert "league_pos" in result.columns
    # Positions should be normalized between 0 and 1
    positions = result["league_pos"].dropna()
    assert (positions >= 0).all()
    assert (positions <= 1).all()


def test_h2h_features_computed():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    assert "h2h_win_rate" in result.columns
    assert "h2h_avg_goals" in result.columns
    assert "h2h_matches" in result.columns
    # First match of Arsenal vs Chelsea: no prior H2H, defaults expected
    arsenal = result[result["team"] == "Arsenal"].sort_values("match_date")
    first = arsenal.iloc[0]
    assert first["h2h_win_rate"] == 0.5
    assert first["h2h_matches"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_features.py::test_league_position_computed tests/test_features.py::test_h2h_features_computed -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Implement `_compute_league_position`**

Add as a module-level function in `backend/services/features.py`:

```python
def _compute_league_position(expanded: pd.DataFrame) -> pd.Series:
    expanded = expanded.copy()
    expanded["match_date"] = pd.to_datetime(expanded["match_date"])
    expanded["season"] = expanded["match_date"].apply(
        lambda d: d.year if d.month >= 7 else d.year - 1
    )
    expanded["points"] = expanded["win"].astype(int) * 3 + expanded["draw"].astype(int)
    expanded["cum_points"] = expanded.groupby(["division", "season", "team"])["points"].cumsum()
    expanded["cum_points_prior"] = expanded.groupby(
        ["division", "season", "team"]
    )["cum_points"].shift(1).fillna(0)

    positions = []
    for idx, row in expanded.iterrows():
        div_season = expanded[
            (expanded["division"] == row["division"])
            & (expanded["season"] == row["season"])
            & (expanded["match_date"] <= row["match_date"])
        ]
        if div_season.empty:
            positions.append(0.5)
            continue
        latest = div_season.groupby("team")["cum_points_prior"].last()
        if len(latest) <= 1:
            positions.append(0.5)
            continue
        rank = latest.rank(ascending=False, method="min")
        n_teams = len(rank)
        team_rank = rank.get(row["team"], n_teams / 2)
        positions.append(round((team_rank - 1) / (n_teams - 1), 4))

    return pd.Series(positions, index=expanded.index)
```

Note: This row-by-row approach is O(n²). For 100K+ rows it would be slow. Use a vectorized approach instead:

```python
def _compute_league_position(expanded: pd.DataFrame) -> pd.Series:
    df = expanded.copy()
    df["match_date"] = pd.to_datetime(df["match_date"])
    df["season"] = df["match_date"].apply(lambda d: d.year if d.month >= 7 else d.year - 1)
    df["points"] = df["win"].astype(int) * 3 + df["draw"].astype(int)

    df["cum_points"] = df.groupby(["division", "season", "team"])["points"].cumsum()
    df["cum_points_prior"] = df.groupby(["division", "season", "team"])["cum_points"].shift(1)
    df["cum_points_prior"] = df["cum_points_prior"].fillna(0)

    def _rank_in_group(group):
        ranked = group["cum_points_prior"].rank(ascending=False, method="min")
        n_teams = group.groupby("team").ngroups
        if n_teams <= 1:
            return pd.Series(0.5, index=group.index)
        return ((ranked - 1) / (n_teams - 1)).round(4)

    result = df.groupby(["division", "season", "match_date"], group_keys=False).apply(
        _rank_in_group
    )
    return result.reindex(expanded.index, fill_value=0.5)
```

- [ ] **Step 4: Implement `_compute_h2h_features`**

Add as a module-level function in `backend/services/features.py`:

```python
def _compute_h2h_features(expanded: pd.DataFrame) -> pd.DataFrame:
    df = expanded.copy()
    df["match_date"] = pd.to_datetime(df["match_date"])

    h2h_win_rate = []
    h2h_avg_goals = []
    h2h_matches_count = []

    global_avg_goals = (df["goals_scored"] + df["goals_conceded"]).mean() / 2
    if pd.isna(global_avg_goals):
        global_avg_goals = 2.5

    for _, row in df.iterrows():
        team = row["team"]
        opponent = row["opponent"]
        date = row["match_date"]

        prior = df[
            (df["team"] == team)
            & (df["opponent"] == opponent)
            & (df["match_date"] < date)
        ]

        if prior.empty:
            h2h_win_rate.append(0.5)
            h2h_avg_goals.append(round(global_avg_goals, 2))
            h2h_matches_count.append(0)
        else:
            wins = prior["win"].sum()
            total = len(prior)
            h2h_win_rate.append(round(wins / total, 4))
            avg_g = (prior["goals_scored"] + prior["goals_conceded"]).mean()
            h2h_avg_goals.append(round(float(avg_g), 2))
            h2h_matches_count.append(min(total, 10))

    return pd.DataFrame({
        "h2h_win_rate": h2h_win_rate,
        "h2h_avg_goals": h2h_avg_goals,
        "h2h_matches": h2h_matches_count,
    }, index=expanded.index)
```

- [ ] **Step 5: Integrate into `compute_team_features`**

In `compute_team_features`, add after the venue splits code (before `logger.info`):

```python
    expanded["league_pos"] = _compute_league_position(expanded)

    h2h = _compute_h2h_features(expanded)
    expanded["h2h_win_rate"] = h2h["h2h_win_rate"]
    expanded["h2h_avg_goals"] = h2h["h2h_avg_goals"]
    expanded["h2h_matches"] = h2h["h2h_matches"]
```

- [ ] **Step 6: Run tests**

Run: `PYTHONPATH=. python3 -m pytest tests/test_features.py -v`
Expected: PASS

- [ ] **Step 7: Lint check**

Run: `python3 -m ruff check backend/services/features.py && python3 -m ruff format --check backend/services/features.py`
Expected: No errors

- [ ] **Step 8: Commit**

```bash
git add backend/services/features.py tests/test_features.py
git commit -m "feat: add league_pos and H2H features"
```

---

### Task 7: Register New Features in Config and build_match_features

**Files:**
- Modify: `backend/ml/config.py`
- Modify: `backend/ml/features.py`
- Modify: `tests/test_ml_features.py`

- [ ] **Step 1: Add new feature lists to `backend/ml/config.py`**

Add after the `_CONTEXT` line (before `BASE_FEATURES`):

```python
_MATCHDAY = ["home_rest_days", "away_rest_days"]

_STANDINGS = ["home_league_pos", "away_league_pos", "league_pos_diff"]

_H2H = ["h2h_home_win_rate", "h2h_avg_goals", "h2h_matches"]

_VENUE = [
    "home_venue_win_rate",
    "home_venue_goals_avg",
    "away_venue_win_rate",
    "away_venue_goals_avg",
]
```

Update `BASE_FEATURES`:

```python
BASE_FEATURES = (
    _HOME_BASE + _HOME_MULTI_WINDOW + _AWAY_BASE + _AWAY_MULTI_WINDOW
    + _CONTEXT + _MATCHDAY + _STANDINGS + _H2H + _VENUE
)
```

Update `PREMIUM_FEATURES`:

```python
PREMIUM_FEATURES = (
    _HOME_BASE
    + _HOME_MULTI_WINDOW
    + _HOME_XG
    + _AWAY_BASE
    + _AWAY_MULTI_WINDOW
    + _AWAY_XG
    + _CONTEXT
    + _MATCHDAY
    + _STANDINGS
    + _H2H
    + _VENUE
)
```

- [ ] **Step 2: Update `_TEAM_ROLLING_COLS` in `backend/ml/features.py`**

Add the new team-level columns that need home/away prefixing:

```python
_TEAM_ROLLING_COLS = [
    "goals_scored_avg",
    "goals_conceded_avg",
    "shots_target_avg",
    "corners_avg",
    "win_rate",
    "draw_rate",
    "btts_rate",
    "over25_rate",
    "xg_for_avg",
    "xg_against_avg",
    "xg_diff_avg",
    "xg_overperformance",
    "goals_scored_avg_3",
    "goals_conceded_avg_3",
    "win_rate_3",
    "goals_scored_avg_10",
    "goals_conceded_avg_10",
    "win_rate_10",
    "rest_days",
    "venue_win_rate",
    "venue_goals_avg",
    "league_pos",
]
```

- [ ] **Step 3: Add H2H and league_pos_diff to `build_match_features`**

In `backend/ml/features.py`, after the `elo_diff` line, add:

```python
    merged["league_pos_diff"] = merged["home_league_pos"] - merged["away_league_pos"]
```

For H2H columns, they need special handling because they're per-match, not per-team with home/away prefix. Add H2H merge columns to `_TEAM_ROLLING_COLS` list would prefix them as `home_h2h_*` and `away_h2h_*`, but the spec wants unprefixed `h2h_home_win_rate`. Instead, handle H2H separately.

Add to `_MATCH_MERGE_COLS`:

```python
_MATCH_MERGE_COLS = [
    "home_elo",
    "away_elo",
    "odd_home",
    "odd_draw",
    "odd_away",
    "odd_over25",
    "odd_under25",
    "ft_home_goals",
    "ft_away_goals",
    "ft_result",
]
```

Actually, H2H features are per team-row (computed in `compute_team_features`). They get prefixed as `home_h2h_win_rate` and `away_h2h_win_rate` via `_TEAM_ROLLING_COLS`. Update the config to match:

In `backend/ml/config.py`, change `_H2H` to use prefixed names:

```python
_H2H = ["home_h2h_win_rate", "home_h2h_avg_goals", "home_h2h_matches",
        "away_h2h_win_rate", "away_h2h_avg_goals", "away_h2h_matches"]
```

And add H2H columns to `_TEAM_ROLLING_COLS` in `features.py`:

```python
    "h2h_win_rate",
    "h2h_avg_goals",
    "h2h_matches",
```

- [ ] **Step 4: Update test fixtures in `tests/test_ml_features.py`**

The `_make_team_features()` function needs the new columns. Add to each team-row dict:

```python
                "rest_days": 7,
                "venue_win_rate": 0.6,
                "venue_goals_avg": 1.5,
                "league_pos": 0.2,
                "h2h_win_rate": 0.5,
                "h2h_avg_goals": 2.5,
                "h2h_matches": 3,
```

Add these to all 4 row dicts in `_make_team_features()` (vary values slightly per row for realism):

Row 1 (Arsenal home): `rest_days=7, venue_win_rate=0.6, venue_goals_avg=1.5, league_pos=0.2, h2h_win_rate=0.6, h2h_avg_goals=2.8, h2h_matches=5`

Row 2 (Chelsea away): `rest_days=4, venue_win_rate=0.3, venue_goals_avg=0.8, league_pos=0.4, h2h_win_rate=0.4, h2h_avg_goals=2.8, h2h_matches=5`

Row 3 (Chelsea home): `rest_days=14, venue_win_rate=0.4, venue_goals_avg=1.0, league_pos=0.35, h2h_win_rate=0.35, h2h_avg_goals=2.5, h2h_matches=4`

Row 4 (Arsenal away): `rest_days=14, venue_win_rate=0.5, venue_goals_avg=1.2, league_pos=0.15, h2h_win_rate=0.65, h2h_avg_goals=2.5, h2h_matches=4`

- [ ] **Step 5: Write test for new columns**

Add to `tests/test_ml_features.py`:

```python
def test_build_match_features_has_new_features():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    new_cols = [
        "home_rest_days", "away_rest_days",
        "home_league_pos", "away_league_pos", "league_pos_diff",
        "home_h2h_win_rate", "home_h2h_avg_goals", "home_h2h_matches",
        "away_h2h_win_rate", "away_h2h_avg_goals", "away_h2h_matches",
        "home_venue_win_rate", "home_venue_goals_avg",
        "away_venue_win_rate", "away_venue_goals_avg",
    ]
    for col in new_cols:
        assert col in result.columns, f"Missing column: {col}"


def test_league_pos_diff():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    row = result.iloc[0]
    expected = row["home_league_pos"] - row["away_league_pos"]
    assert row["league_pos_diff"] == pytest.approx(expected)
```

- [ ] **Step 6: Run all ML feature tests**

Run: `PYTHONPATH=. python3 -m pytest tests/test_ml_features.py -v`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `PYTHONPATH=. python3 -m pytest tests/ -v`
Expected: PASS (some tests that import BASE_FEATURES/PREMIUM_FEATURES will now have 44/52 features)

- [ ] **Step 8: Lint check**

Run: `python3 -m ruff check backend/ml/config.py backend/ml/features.py tests/test_ml_features.py && python3 -m ruff format --check backend/ml/config.py backend/ml/features.py tests/test_ml_features.py`
Expected: No errors

- [ ] **Step 9: Commit**

```bash
git add backend/ml/config.py backend/ml/features.py tests/test_ml_features.py
git commit -m "feat: register 13 new features in config and build_match_features"
```

---

### Task 8: Dashboard — Performance Filters

**Files:**
- Modify: `dashboard/views/5_value_bets.py`

- [ ] **Step 1: Add performance filter selectboxes**

In `dashboard/views/5_value_bets.py`, after the `st.markdown(section_header("📈", "Rendimiento Historico"), ...)` line and the `get_resolved_picks()` call, add:

```python
if resolved_picks:
    st.markdown("**Filtrar rendimiento:**")
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        perf_league = st.selectbox(
            "Liga",
            ["Todas"] + list(DIVISION_NAMES.keys()),
            format_func=lambda x: "Todas" if x == "Todas" else DIVISION_NAMES.get(x, x),
            key="perf_league",
        )
    with fc2:
        perf_market = st.selectbox(
            "Mercado",
            ["Todos", "1X2", "Over/Under"],
            key="perf_market",
        )
    with fc3:
        perf_confidence = st.selectbox(
            "Confianza",
            ["Todas", "alta", "media", "baja"],
            format_func=lambda x: x.capitalize(),
            key="perf_confidence",
        )
    with fc4:
        perf_model = st.selectbox(
            "Modelo",
            ["Todos", "base", "premium"],
            format_func=lambda x: x.capitalize(),
            key="perf_model",
        )

    filtered = resolved_picks
    if perf_league != "Todas":
        filtered = [p for p in filtered if p.get("division") == perf_league]
    if perf_market == "1X2":
        filtered = [p for p in filtered if p.get("market", "").startswith("1x2")]
    elif perf_market == "Over/Under":
        filtered = [p for p in filtered if p.get("market") in ("over25", "under25")]
    if perf_confidence != "Todas":
        filtered = [p for p in filtered if p.get("confidence") == perf_confidence]
    if perf_model != "Todos":
        filtered = [p for p in filtered if p.get("model_variant") == perf_model]

    perf = calculate_performance(filtered)
    performance_kpis(perf)
    # ... rest of the performance section uses `filtered` instead of `resolved_picks`
```

Update the remaining performance section to use `filtered` instead of `resolved_picks`:

```python
    st.markdown(section_header("📊", "Desglose por Mercado"), unsafe_allow_html=True)
    breakdown = market_breakdown_table(perf)
    if not breakdown.empty:
        st.dataframe(breakdown, use_container_width=True, hide_index=True)

    st.markdown(section_header("💰", "Profit Acumulado"), unsafe_allow_html=True)
    chart = profit_chart(filtered)
    if chart:
        st.plotly_chart(chart, use_container_width=True)

    st.markdown(section_header("📋", "Ultimos 20 Picks Resueltos"), unsafe_allow_html=True)
    recent = filtered[:20]
    resolved_display = format_resolved(recent)
    if not resolved_display.empty:
        st.dataframe(resolved_display, use_container_width=True, hide_index=True)
```

- [ ] **Step 2: Lint check**

Run: `python3 -m ruff check dashboard/views/5_value_bets.py && python3 -m ruff format --check dashboard/views/5_value_bets.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add dashboard/views/5_value_bets.py
git commit -m "feat: add performance filters by league, market, confidence, model"
```

---

### Task 9: Integration Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `PYTHONPATH=. python3 -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Verify feature counts**

Run: `PYTHONPATH=. python3 -c "from backend.ml.config import BASE_FEATURES, PREMIUM_FEATURES; print(f'BASE: {len(BASE_FEATURES)}'); print(f'PREMIUM: {len(PREMIUM_FEATURES)}')"`
Expected: BASE: 46, PREMIUM: 54

- [ ] **Step 3: Verify vig removal works end-to-end**

Run: `PYTHONPATH=. python3 -c "from backend.betting.value import remove_vig, calculate_edge; fair = remove_vig([1.90, 3.40, 4.20]); print(f'Fair probs sum: {sum(fair):.4f}'); edge = calculate_edge(0.55, 0, [1.90, 3.40, 4.20]); print(f'Edge: {edge}')"`
Expected: Fair probs sum: 1.0000, Edge dict with positive edge

- [ ] **Step 4: Lint all modified files**

Run: `python3 -m ruff check backend/ dashboard/ scripts/ tests/ && python3 -m ruff format --check backend/ dashboard/ scripts/ tests/`
Expected: No errors

- [ ] **Step 5: Final commit if any formatting fixes needed**

```bash
git add -A
git diff --cached --quiet || git commit -m "chore: lint fixes"
```
