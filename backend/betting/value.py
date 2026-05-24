import logging

logger = logging.getLogger(__name__)

MIN_EDGE = 0.08


def remove_vig(odds: list[float]) -> list[float]:
    if len(odds) < 2:
        return [1 / odds[0]]
    raw = [1 / o for o in odds]
    overround = sum(raw)
    return [p / overround for p in raw]


def calculate_edge(model_prob: float, selection_index: int, market_odds: list[float]) -> dict:
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


def classify_stake(edge: float, confidence: str) -> int:
    if edge > 0.15 and confidence == "alta":
        return 3
    if edge > 0.10 and confidence in ("alta", "media"):
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

        h2h_odds = [
            o
            for o in [odds.get("odd_home"), odds.get("odd_draw"), odds.get("odd_away")]
            if o is not None and o > 1.0
        ]
        if len(h2h_odds) >= 2:
            full_h2h = [odds.get("odd_home"), odds.get("odd_draw"), odds.get("odd_away")]
            if odds.get("odd_home") and odds["odd_home"] > 1.0:
                candidates.append(("1x2_home", "H", pred["prob_home"], full_h2h, 0))
            if odds.get("odd_draw") and odds["odd_draw"] > 1.0:
                candidates.append(("1x2_draw", "D", pred["prob_draw"], full_h2h, 1))
            if odds.get("odd_away") and odds["odd_away"] > 1.0:
                candidates.append(("1x2_away", "A", pred["prob_away"], full_h2h, 2))

        totals_odds = [
            o
            for o in [odds.get("odd_over25"), odds.get("odd_under25")]
            if o is not None and o > 1.0
        ]
        if len(totals_odds) >= 2:
            full_totals = [odds.get("odd_over25"), odds.get("odd_under25")]
            if odds.get("odd_over25") and odds["odd_over25"] > 1.0:
                candidates.append(("over25", "Over", pred["prob_over25"], full_totals, 0))
            if odds.get("odd_under25") and odds["odd_under25"] > 1.0:
                prob_under = 1 - pred["prob_over25"] if pred.get("prob_over25") else None
                if prob_under is not None:
                    candidates.append(("under25", "Under", prob_under, full_totals, 1))

        best_h2h = None
        best_totals = None

        for market, selection, model_prob, mkt_odds, sel_idx in candidates:
            if model_prob is None:
                continue

            calc = calculate_edge(model_prob, sel_idx, mkt_odds)
            stake = classify_stake(calc["edge"], pred.get("confidence", "baja"))
            if stake == 0:
                continue

            pick = {
                "match_date": pred["match_date"],
                "home_team": pred["home_team"],
                "away_team": pred["away_team"],
                "division": pred["division"],
                "market": market,
                "selection": selection,
                "model_prob": round(model_prob, 4),
                "implied_prob": calc["implied_prob"],
                "edge": calc["edge"],
                "odd": mkt_odds[sel_idx],
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

            if market.startswith("1x2"):
                if best_h2h is None or calc["edge"] > best_h2h["edge"]:
                    best_h2h = pick
            else:
                if best_totals is None or calc["edge"] > best_totals["edge"]:
                    best_totals = pick

        if best_h2h:
            picks.append(best_h2h)
        if best_totals:
            picks.append(best_totals)

    logger.info("Generated %d picks from %d predictions", len(picks), len(predictions))
    return picks
