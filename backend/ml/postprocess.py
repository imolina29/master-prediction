"""League post-processing: Poisson ensemble + draw intelligence.

Ports the WC-proven techniques (Poisson Dixon-Coles blend, draw zone,
tight-margin draw preference) to European league predictions.
"""

import logging

import numpy as np

from backend.advisor.poisson import estimate_score
from backend.ml.league_config import (
    LEAGUE_DRAW_ZONE_ELO_MAX,
    LEAGUE_DRAW_ZONE_SPREAD,
    LEAGUE_DRAW_ZONE_THRESHOLD,
    LEAGUE_ENSEMBLE_POISSON,
    LEAGUE_ENSEMBLE_XGB,
    LEAGUE_GLOBAL_AVG,
    LEAGUE_HOME_ADVANTAGE,
    LEAGUE_TIGHT_MARGIN,
)

logger = logging.getLogger(__name__)

DEFAULT_ELO = 1500.0


def _pick_result(probs: list[float]) -> str:
    """Pick predicted result; prefer Draw when top two probabilities are within TIGHT_MARGIN."""
    labels = ["H", "D", "A"]
    sorted_idx = sorted(range(3), key=lambda i: -probs[i])
    top, second = sorted_idx[0], sorted_idx[1]
    if probs[top] - probs[second] < LEAGUE_TIGHT_MARGIN and labels[second] == "D":
        return "D"
    if probs[top] - probs[second] < LEAGUE_TIGHT_MARGIN and labels[top] == "D":
        return "D"
    return labels[top]


def _classify_confidence(max_prob: float) -> str:
    if max_prob > 0.60:
        return "alta"
    if max_prob > 0.45:
        return "media"
    return "baja"


def get_league_poisson_probs(
    home_goals_avg3: float | None,
    home_conceded_avg3: float | None,
    away_goals_avg3: float | None,
    away_conceded_avg3: float | None,
    home_elo: float,
    away_elo: float,
    division: str,
) -> dict | None:
    """Run Poisson Dixon-Coles using 3-match form as attack/defense ratings."""
    if any(
        v is None or (isinstance(v, float) and np.isnan(v))
        for v in [home_goals_avg3, home_conceded_avg3, away_goals_avg3, away_conceded_avg3]
    ):
        logger.warning("Missing 3-match averages for Poisson, skipping ensemble")
        return None

    home_adv = LEAGUE_HOME_ADVANTAGE.get(division, 1.10)
    global_avg = LEAGUE_GLOBAL_AVG.get(division, 1.30)

    try:
        return estimate_score(
            home_attack=home_goals_avg3,
            home_defense=home_conceded_avg3,
            away_attack=away_goals_avg3,
            away_defense=away_conceded_avg3,
            home_elo=home_elo,
            away_elo=away_elo,
            global_avg=global_avg,
            home_advantage=home_adv,
        )
    except Exception as e:
        logger.warning("Poisson estimate failed: %s", e)
        return None


def apply_league_ensemble(preds: dict, poisson: dict | None) -> dict:
    """Blend XGBoost (70%) + Poisson (30%) probabilities for league matches."""
    if poisson is None:
        return preds

    w_xgb = LEAGUE_ENSEMBLE_XGB
    w_poi = LEAGUE_ENSEMBLE_POISSON

    h = w_xgb * preds["prob_home"] + w_poi * poisson["prob_home"]
    d = w_xgb * preds["prob_draw"] + w_poi * poisson["prob_draw"]
    a = w_xgb * preds["prob_away"] + w_poi * poisson["prob_away"]

    preds["prob_home"] = round(h, 4)
    preds["prob_draw"] = round(d, 4)
    preds["prob_away"] = round(a, 4)

    if poisson.get("prob_over25") is not None and preds.get("prob_over25") is not None:
        preds["prob_over25"] = round(
            w_xgb * preds["prob_over25"] + w_poi * poisson["prob_over25"], 4
        )
    if poisson.get("prob_btts") is not None and preds.get("prob_btts") is not None:
        preds["prob_btts"] = round(w_xgb * preds["prob_btts"] + w_poi * poisson["prob_btts"], 4)

    probs = [h, d, a]
    max_prob = max(probs)
    xgb_result = preds.get("predicted_result")
    poisson_probs = [poisson["prob_home"], poisson["prob_draw"], poisson["prob_away"]]
    poisson_result = ["H", "D", "A"][int(np.argmax(poisson_probs))]

    preds["predicted_result"] = _pick_result(probs)

    if xgb_result == poisson_result:
        if max_prob > 0.50:
            preds["confidence"] = "alta"
        else:
            preds["confidence"] = "media"
        logger.info(
            "League ensemble AGREE (%s): XGB+Poisson → confidence=%s",
            xgb_result,
            preds["confidence"],
        )
    else:
        if max_prob > 0.55:
            preds["confidence"] = "media"
        else:
            preds["confidence"] = "baja"
        logger.info(
            "League ensemble DIVERGE: XGB=%s Poisson=%s → %s (confidence=%s)",
            xgb_result,
            poisson_result,
            preds["predicted_result"],
            preds["confidence"],
        )

    return preds


def apply_league_draw_zone(
    preds: dict,
    elo_diff: float,
    home_elo: float = DEFAULT_ELO,
    away_elo: float = DEFAULT_ELO,
) -> dict:
    """Override prediction to Draw when conditions indicate a tight match."""
    if home_elo == DEFAULT_ELO and away_elo == DEFAULT_ELO:
        return preds

    h = preds["prob_home"]
    d = preds["prob_draw"]
    a = preds["prob_away"]
    spread = max(h, d, a) - min(h, d, a)

    if (
        d >= LEAGUE_DRAW_ZONE_THRESHOLD
        and spread < LEAGUE_DRAW_ZONE_SPREAD
        and abs(elo_diff) < LEAGUE_DRAW_ZONE_ELO_MAX
    ):
        preds["predicted_result"] = "D"
        preds["confidence"] = _classify_confidence(d)
        logger.info(
            "League draw zone triggered: D=%.0f%% spread=%.0f%% elo_diff=%.0f",
            d * 100,
            spread * 100,
            elo_diff,
        )

    return preds
