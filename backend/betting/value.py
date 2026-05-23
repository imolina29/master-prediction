import logging

logger = logging.getLogger(__name__)

MIN_EDGE = 0.08


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
