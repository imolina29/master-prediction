import argparse
import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


WC_HOST_COUNTRIES = {"United States", "Canada", "Mexico"}
WC_HOST_BOOST = 0.08
WC_DRAW_BOOST = 0.25

WC_DRAW_ZONE_THRESHOLD = 0.30
WC_DRAW_ZONE_SPREAD = 0.12
WC_DRAW_ZONE_ELO_MAX = 80

ENSEMBLE_WEIGHT_XGBOOST = 0.70
ENSEMBLE_WEIGHT_POISSON = 0.30

TOURNAMENT_FORM_WEIGHT = 0.65
HISTORICAL_FORM_WEIGHT = 0.35

TIGHT_MARGIN = 0.05


def _pick_result(probs: list[float]) -> str:
    """Pick predicted result; prefer Draw when top two probabilities are within TIGHT_MARGIN."""
    labels = ["H", "D", "A"]
    sorted_idx = sorted(range(3), key=lambda i: -probs[i])
    top, second = sorted_idx[0], sorted_idx[1]
    if probs[top] - probs[second] < TIGHT_MARGIN and labels[second] == "D":
        return "D"
    if probs[top] - probs[second] < TIGHT_MARGIN and labels[top] == "D":
        return "D"
    return labels[top]


WC_GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Korea", "Czechia", "South Africa"],
    "B": ["Canada", "Bosnia Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["France", "Norway", "Senegal", "Iraq"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde Islands"],
    "I": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Colombia", "Congo DR", "Uzbekistan"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

TEAM_TO_GROUP: dict[str, str] = {}
for _grp, _teams in WC_GROUPS.items():
    for _t in _teams:
        TEAM_TO_GROUP[_t] = _grp


def _apply_host_boost(preds: dict, home: str, division: str) -> dict:
    if division != "WC" or home not in WC_HOST_COUNTRIES:
        return preds
    h = preds["prob_home"]
    d = preds["prob_draw"]
    a = preds["prob_away"]
    total_da = d + a
    if total_da <= 0:
        return preds
    preds["prob_home"] = round(h + WC_HOST_BOOST, 4)
    preds["prob_draw"] = round(d - WC_HOST_BOOST * (d / total_da), 4)
    preds["prob_away"] = round(a - WC_HOST_BOOST * (a / total_da), 4)
    probs = [preds["prob_home"], preds["prob_draw"], preds["prob_away"]]
    preds["predicted_result"] = _pick_result(probs)
    preds["confidence"] = _classify_confidence_wc(max(probs))
    logger.info("Applied host boost for %s: H=%.0f%%", home, preds["prob_home"] * 100)
    return preds


def _apply_wc_draw_boost(preds: dict, division: str) -> dict:
    if division != "WC":
        return preds
    h = preds["prob_home"]
    d = preds["prob_draw"]
    a = preds["prob_away"]
    d_boosted = d * (1 + WC_DRAW_BOOST)
    total = h + d_boosted + a
    preds["prob_home"] = round(h / total, 4)
    preds["prob_draw"] = round(d_boosted / total, 4)
    preds["prob_away"] = round(a / total, 4)
    probs = [preds["prob_home"], preds["prob_draw"], preds["prob_away"]]
    preds["predicted_result"] = _pick_result(probs)
    preds["confidence"] = _classify_confidence_wc(max(probs))
    logger.info("Applied WC draw boost: D=%.0f%%", preds["prob_draw"] * 100)
    return preds


def _apply_draw_zone(
    preds: dict,
    division: str,
    elo_diff: float,
    home: str,
    away: str,
) -> dict:
    """Detect draw-prone matches where model spreads are tight."""
    if division != "WC":
        return preds
    if home in WC_HOST_COUNTRIES or away in WC_HOST_COUNTRIES:
        return preds
    h = preds["prob_home"]
    d = preds["prob_draw"]
    a = preds["prob_away"]
    spread = max(h, d, a) - min(h, d, a)

    if (
        d >= WC_DRAW_ZONE_THRESHOLD
        and spread < WC_DRAW_ZONE_SPREAD
        and abs(elo_diff) < WC_DRAW_ZONE_ELO_MAX
    ):
        preds["predicted_result"] = "D"
        preds["confidence"] = _classify_confidence_wc(d)
        logger.info(
            "Draw zone triggered: D=%.0f%% spread=%.0f%% elo_diff=%.0f",
            d * 100,
            spread * 100,
            elo_diff,
        )
    return preds


# ---------------------------------------------------------------------------
# Tournament Form Override (matchday 3)
# ---------------------------------------------------------------------------


def _build_group_standings(
    wc_played: list[dict],
) -> dict[str, dict[str, dict]]:
    """Build group tables from played WC matches. Returns {group: {team: stats}}."""
    standings: dict[str, dict[str, dict]] = {}
    for grp, teams in WC_GROUPS.items():
        standings[grp] = {}
        for t in teams:
            standings[grp][t] = {
                "pts": 0,
                "gf": 0,
                "ga": 0,
                "gd": 0,
                "w": 0,
                "d": 0,
                "l": 0,
                "played": 0,
            }

    for m in wc_played:
        home = m["home_team"]
        away = m["away_team"]
        hg = m.get("ft_home_goals")
        ag = m.get("ft_away_goals")
        if hg is None or ag is None:
            continue

        grp = TEAM_TO_GROUP.get(home)
        if not grp or grp != TEAM_TO_GROUP.get(away):
            continue

        for team, gf, ga in [(home, hg, ag), (away, ag, hg)]:
            s = standings[grp][team]
            s["played"] += 1
            s["gf"] += gf
            s["ga"] += ga
            s["gd"] = s["gf"] - s["ga"]
            if gf > ga:
                s["pts"] += 3
                s["w"] += 1
            elif gf == ga:
                s["pts"] += 1
                s["d"] += 1
            else:
                s["l"] += 1

    return standings


def _get_best_third_place_cutoff(
    standings: dict[str, dict[str, dict]],
) -> int:
    """Estimate the points cutoff to qualify as best 3rd place.

    8 of 12 third-place teams qualify. Returns the current 8th-place pts.
    """
    thirds = []
    for grp, table in standings.items():
        sorted_t = sorted(
            table.items(),
            key=lambda x: (x[1]["pts"], x[1]["gd"], x[1]["gf"]),
            reverse=True,
        )
        if len(sorted_t) >= 3:
            thirds.append(sorted_t[2][1])

    thirds.sort(key=lambda x: (x["pts"], x["gd"], x["gf"]), reverse=True)
    return thirds[7]["pts"] if len(thirds) >= 8 else 0


def _classify_motivation(
    team: str,
    standings: dict[str, dict[str, dict]],
) -> str:
    """Classify team motivation for matchday 3.

    Returns: 'qualified', 'fight_first', 'must_win', 'draw_ok', 'eliminated', 'unknown'.
    - fight_first: safe but competing for 1st place (better R16 bracket).
    Accounts for best-third-place qualification (8 of 12 thirds advance).
    """
    grp = TEAM_TO_GROUP.get(team)
    if not grp or grp not in standings:
        return "unknown"

    table = standings[grp]
    team_stats = table.get(team)
    if not team_stats or team_stats["played"] < 2:
        return "unknown"

    sorted_teams = sorted(
        table.items(),
        key=lambda x: (x[1]["pts"], x[1]["gd"], x[1]["gf"]),
        reverse=True,
    )
    rank = next(i for i, (t, _) in enumerate(sorted_teams) if t == team) + 1
    pts = team_stats["pts"]
    gd = team_stats["gd"]

    if rank <= 2 and pts >= 6:
        first_pts = sorted_teams[0][1]["pts"]
        second_pts = sorted_teams[1][1]["pts"]
        if first_pts == second_pts:
            return "fight_first"
        return "qualified"
    if rank <= 2 and pts >= 4:
        first_pts = sorted_teams[0][1]["pts"]
        second_pts = sorted_teams[1][1]["pts"]
        if first_pts == second_pts:
            return "fight_first"
        return "draw_ok"
    if rank == 3 and pts >= 3:
        return "draw_ok"

    third_cutoff = _get_best_third_place_cutoff(standings)
    max_possible_pts = pts + 3

    if rank == 3:
        if max_possible_pts > third_cutoff:
            return "must_win"
        if max_possible_pts == third_cutoff and gd > -4:
            return "must_win"
        return "eliminated"

    if rank == 4:
        can_reach_third = False
        third_team = sorted_teams[2] if len(sorted_teams) >= 3 else None
        if third_team:
            third_pts = third_team[1]["pts"]
            can_reach_third = max_possible_pts > third_pts or (
                max_possible_pts == third_pts and gd + 3 > third_team[1]["gd"]
            )

        if can_reach_third and max_possible_pts >= third_cutoff:
            return "must_win"

        if pts == 0 and gd <= -4:
            return "eliminated"
        if max_possible_pts < third_cutoff:
            return "eliminated"

        return "must_win"

    return "must_win"


def _build_tournament_form(
    team: str,
    wc_played: list[dict],
) -> dict | None:
    """Build tournament-specific features from WC matches played by this team."""
    games: list[dict] = []
    for m in wc_played:
        hg = m.get("ft_home_goals")
        ag = m.get("ft_away_goals")
        if hg is None or ag is None:
            continue
        if m["home_team"] == team:
            games.append({"gf": hg, "ga": ag})
        elif m["away_team"] == team:
            games.append({"gf": ag, "ga": hg})

    if len(games) < 2:
        return None

    n = len(games)
    gf_avg = sum(g["gf"] for g in games) / n
    ga_avg = sum(g["ga"] for g in games) / n
    wins = sum(1 for g in games if g["gf"] > g["ga"])
    draws = sum(1 for g in games if g["gf"] == g["ga"])
    btts = sum(1 for g in games if g["gf"] > 0 and g["ga"] > 0)
    over25 = sum(1 for g in games if g["gf"] + g["ga"] > 2)

    return {
        "goals_scored_avg": round(gf_avg, 3),
        "goals_conceded_avg": round(ga_avg, 3),
        "win_rate": round(wins / n, 3),
        "draw_rate": round(draws / n, 3),
        "btts_rate": round(btts / n, 3),
        "over25_rate": round(over25 / n, 3),
        "matches": n,
    }


def _apply_tournament_form_override(
    features: dict[str, dict],
    wc_played: list[dict],
    matchday: int,
) -> dict[str, dict]:
    """From matchday 3 onward, blend tournament form (65%) with historical (35%)."""
    if matchday < 3:
        return features

    features = {k: dict(v) for k, v in features.items()}
    blend_keys = [
        "goals_scored_avg",
        "goals_conceded_avg",
        "win_rate",
        "draw_rate",
        "btts_rate",
        "over25_rate",
    ]

    updated = 0
    for team in list(features.keys()):
        tf = _build_tournament_form(team, wc_played)
        if not tf:
            continue

        feat = features[team]
        for key in blend_keys:
            hist_val = feat.get(key, 0.0)
            tourn_val = tf.get(key, 0.0)
            feat[key] = round(
                TOURNAMENT_FORM_WEIGHT * tourn_val + HISTORICAL_FORM_WEIGHT * hist_val, 3
            )

        feat["goals_scored_avg_3"] = tf["goals_scored_avg"]
        feat["goals_conceded_avg_3"] = tf["goals_conceded_avg"]
        feat["win_rate_3"] = tf["win_rate"]
        updated += 1

    logger.info("Tournament form override applied to %d teams (matchday %d)", updated, matchday)
    return features


def _apply_draw_context_boost(
    preds: dict,
    home: str,
    away: str,
    division: str,
    standings: dict[str, dict[str, dict]],
    matchday: int,
) -> dict:
    """Adjust draw probability based on both teams' motivation in matchday 3."""
    if division != "WC" or matchday < 3:
        return preds

    mot_home = _classify_motivation(home, standings)
    mot_away = _classify_motivation(away, standings)

    boost = 0.0
    mots = {mot_home, mot_away}

    if mot_home == "fight_first" and mot_away == "fight_first":
        boost = -0.05
    elif "fight_first" in mots and "must_win" in mots:
        boost = -0.04
    elif "fight_first" in mots:
        boost = 0.0
    elif mot_home == "draw_ok" and mot_away == "draw_ok":
        boost = 0.10
    elif mot_home == "qualified" and mot_away == "qualified":
        boost = 0.08
    elif "draw_ok" in mots and "qualified" in mots:
        boost = 0.06
    elif mot_home == "eliminated" or mot_away == "eliminated":
        boost = -0.06
    elif mot_home == "must_win" and mot_away == "must_win":
        boost = -0.04

    if abs(boost) < 0.001:
        return preds

    h = preds["prob_home"]
    d = preds["prob_draw"]
    a = preds["prob_away"]

    d_new = min(max(d + boost, 0.05), 0.60)
    leftover = d_new - d
    ha_total = h + a
    if ha_total > 0:
        h_new = h - leftover * (h / ha_total)
        a_new = a - leftover * (a / ha_total)
    else:
        h_new = h
        a_new = a

    preds["prob_home"] = round(max(h_new, 0.02), 4)
    preds["prob_draw"] = round(d_new, 4)
    preds["prob_away"] = round(max(a_new, 0.02), 4)

    probs = [preds["prob_home"], preds["prob_draw"], preds["prob_away"]]
    preds["predicted_result"] = _pick_result(probs)
    preds["confidence"] = _classify_confidence_wc(max(probs))

    logger.info(
        "Draw context boost for %s (%s) vs %s (%s): %.0f%% → D=%.0f%%",
        home,
        mot_home,
        away,
        mot_away,
        boost * 100,
        preds["prob_draw"] * 100,
    )
    return preds


def _get_poisson_probs(
    home: str,
    away: str,
    national_features: dict,
    division: str,
) -> dict | None:
    """Run Poisson model and return 1X2 + over25 + btts probabilities."""
    try:
        from backend.advisor.poisson import estimate_score

        hf = national_features.get(home)
        af = national_features.get(away)
        if not hf or not af:
            return None

        all_avgs = [
            f["goals_scored_avg"] for f in national_features.values() if "goals_scored_avg" in f
        ]
        global_avg = sum(all_avgs) / len(all_avgs) if all_avgs else 1.25
        home_advantage = 1.08 if division == "WC" and home in WC_HOST_COUNTRIES else 1.0

        est = estimate_score(
            home_attack=hf["goals_scored_avg"],
            home_defense=hf["goals_conceded_avg"],
            away_attack=af["goals_scored_avg"],
            away_defense=af["goals_conceded_avg"],
            home_elo=hf.get("elo", 1500.0),
            away_elo=af.get("elo", 1500.0),
            global_avg=global_avg,
            home_advantage=home_advantage,
        )
        return est
    except Exception as e:
        logger.warning("Poisson estimate failed for %s vs %s: %s", home, away, e)
        return None


def _apply_ensemble(preds: dict, poisson: dict | None, division: str) -> dict:
    """Blend XGBoost and Poisson probabilities, adjust confidence on agreement."""
    if poisson is None:
        return preds

    w_xgb = ENSEMBLE_WEIGHT_XGBOOST
    w_poi = ENSEMBLE_WEIGHT_POISSON

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
            "Ensemble AGREE (%s): XGB+Poisson → confidence=%s",
            xgb_result,
            preds["confidence"],
        )
    else:
        if max_prob > 0.55:
            preds["confidence"] = "media"
        else:
            preds["confidence"] = "baja"
        logger.info(
            "Ensemble DIVERGE: XGB=%s Poisson=%s → %s (confidence=%s)",
            xgb_result,
            poisson_result,
            preds["predicted_result"],
            preds["confidence"],
        )

    return preds


def _classify_confidence_wc(max_prob: float) -> str:
    if max_prob > 0.60:
        return "alta"
    if max_prob > 0.45:
        return "media"
    return "baja"


def _compute_rest_days(
    team: str,
    match_date: str,
    wc_played: list[dict],
) -> float:
    """Calculate days since team's last WC match."""
    last_date = None
    for m in wc_played:
        if m["match_date"] >= match_date:
            continue
        if m["home_team"] == team or m["away_team"] == team:
            if last_date is None or m["match_date"] > last_date:
                last_date = m["match_date"]
    if last_date is None:
        return 7.0
    from datetime import datetime as dt

    d1 = dt.strptime(match_date, "%Y-%m-%d")
    d2 = dt.strptime(last_date, "%Y-%m-%d")
    return float((d1 - d2).days)


def _compute_matchday(
    home: str,
    away: str,
    match_date: str,
    wc_played: list[dict],
) -> int:
    """Determine which group matchday this is (1, 2, or 3) for these teams."""
    played = 0
    for m in wc_played:
        if m["match_date"] >= match_date:
            continue
        teams = {m["home_team"], m["away_team"]}
        if home in teams or away in teams:
            played += 1
    return min(played // 2 + 1, 3)


def _build_feature_row_from_national(
    features: dict,
    home: str,
    away: str,
    match: dict,
    h2h_stats: dict | None = None,
    wc_played: list[dict] | None = None,
) -> dict:
    home_feat = features.get(home)
    away_feat = features.get(away)
    if not home_feat or not away_feat:
        return {}

    feature_row = {}
    rolling_cols = [
        "goals_scored_avg",
        "goals_conceded_avg",
        "shots_target_avg",
        "corners_avg",
        "win_rate",
        "draw_rate",
        "btts_rate",
        "over25_rate",
        "goals_scored_avg_3",
        "goals_conceded_avg_3",
        "win_rate_3",
        "goals_scored_avg_10",
        "goals_conceded_avg_10",
        "win_rate_10",
    ]
    for col in rolling_cols:
        home_val = home_feat.get(col)
        away_val = away_feat.get(col)
        feature_row[f"home_{col}"] = home_val if home_val is not None else float("nan")
        feature_row[f"away_{col}"] = away_val if away_val is not None else float("nan")

    for col in ["xg_for_avg", "xg_against_avg", "xg_diff_avg", "xg_overperformance"]:
        feature_row[f"home_{col}"] = float("nan")
        feature_row[f"away_{col}"] = float("nan")

    home_elo = home_feat.get("elo") or match.get("home_elo") or 1500.0
    away_elo = away_feat.get("elo") or match.get("away_elo") or 1500.0
    feature_row["home_elo"] = home_elo
    feature_row["away_elo"] = away_elo
    feature_row["elo_diff"] = home_elo - away_elo

    match_date = str(match.get("match_date", ""))
    wc_played = wc_played or []

    feature_row["home_rest_days"] = _compute_rest_days(home, match_date, wc_played)
    feature_row["away_rest_days"] = _compute_rest_days(away, match_date, wc_played)

    h2h_home = (h2h_stats or {}).get((home, away), {})
    h2h_away = (h2h_stats or {}).get((away, home), {})
    feature_row["home_h2h_win_rate"] = h2h_home.get("h2h_win_rate", float("nan"))
    feature_row["home_h2h_avg_goals"] = h2h_home.get("h2h_avg_goals", float("nan"))
    feature_row["home_h2h_matches"] = h2h_home.get("h2h_matches", float("nan"))
    feature_row["away_h2h_win_rate"] = h2h_away.get("h2h_win_rate", float("nan"))
    feature_row["away_h2h_avg_goals"] = h2h_away.get("h2h_avg_goals", float("nan"))
    feature_row["away_h2h_matches"] = h2h_away.get("h2h_matches", float("nan"))

    for col in ["venue_win_rate", "venue_goals_avg", "league_pos"]:
        feature_row[f"home_{col}"] = float("nan")
        feature_row[f"away_{col}"] = float("nan")
    feature_row["league_pos_diff"] = float("nan")

    return feature_row


def _update_features_with_wc_results(
    features: dict[str, dict],
    wc_played: list[dict],
) -> dict[str, dict]:
    """Incorporate WC results into national team rolling averages."""
    features = {k: dict(v) for k, v in features.items()}

    team_wc_matches: dict[str, list[dict]] = {}
    for m in sorted(wc_played, key=lambda x: x["match_date"]):
        hg = m["ft_home_goals"]
        ag = m["ft_away_goals"]
        if hg is None or ag is None:
            continue
        team_wc_matches.setdefault(m["home_team"], []).append({"gf": hg, "ga": ag})
        team_wc_matches.setdefault(m["away_team"], []).append({"gf": ag, "ga": hg})

    updated = 0
    for team, wc_games in team_wc_matches.items():
        feat = features.get(team)
        if not feat:
            continue

        n_pre = feat.get("matches_used", 20)
        pre_gf = feat.get("goals_scored_avg", 0) * n_pre
        pre_ga = feat.get("goals_conceded_avg", 0) * n_pre
        pre_wins = feat.get("win_rate", 0) * n_pre
        pre_draws = feat.get("draw_rate", 0) * n_pre
        pre_btts = feat.get("btts_rate", 0) * n_pre
        pre_o25 = feat.get("over25_rate", 0) * n_pre

        for g in wc_games:
            pre_gf += g["gf"]
            pre_ga += g["ga"]
            if g["gf"] > g["ga"]:
                pre_wins += 1
            elif g["gf"] == g["ga"]:
                pre_draws += 1
            if g["gf"] > 0 and g["ga"] > 0:
                pre_btts += 1
            if g["gf"] + g["ga"] > 2:
                pre_o25 += 1

        n_total = n_pre + len(wc_games)
        feat["goals_scored_avg"] = round(pre_gf / n_total, 3)
        feat["goals_conceded_avg"] = round(pre_ga / n_total, 3)
        feat["win_rate"] = round(pre_wins / n_total, 3)
        feat["draw_rate"] = round(pre_draws / n_total, 3)
        feat["btts_rate"] = round(pre_btts / n_total, 3)
        feat["over25_rate"] = round(pre_o25 / n_total, 3)
        feat["matches_used"] = n_total

        recent3 = wc_games[-3:] if len(wc_games) >= 3 else wc_games
        if recent3:
            n3 = len(recent3)
            feat["goals_scored_avg_3"] = round(sum(g["gf"] for g in recent3) / n3, 3)
            feat["goals_conceded_avg_3"] = round(sum(g["ga"] for g in recent3) / n3, 3)
            feat["win_rate_3"] = round(sum(1 for g in recent3 if g["gf"] > g["ga"]) / n3, 3)

        updated += 1

    logger.info("Updated features for %d teams with %d WC results", updated, len(wc_played))
    return features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upcoming", action="store_true", help="Predict upcoming 7 days")
    parser.parse_args()

    from backend.db.client import get_supabase
    from backend.etl.fixtures import load_h2h_features, load_national_features
    from backend.ml.config import FEATURES_PATH
    from backend.ml.predict import predict_upcoming

    client = get_supabase()

    col_tz = timezone(timedelta(hours=-5))
    now = datetime.now(col_tz)
    today = now.strftime("%Y-%m-%d")
    week_ahead = (now + timedelta(days=21)).strftime("%Y-%m-%d")

    logger.info("Finding matches from %s to %s", today, week_ahead)
    resp = (
        client.table("matches")
        .select("*")
        .gte("match_date", today)
        .lte("match_date", week_ahead)
        .is_("ft_result", "null")
        .execute()
    )
    upcoming = pd.DataFrame(resp.data)

    if upcoming.empty:
        logger.info("No upcoming matches found.")
        return

    # Filter out ghost fixtures: matches the API reports as scheduled but
    # that were already played under a slightly different date (±7 days).
    ghost_ids = []
    window_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    played_resp = (
        client.table("matches")
        .select("division,home_team,away_team,match_date")
        .gte("match_date", window_start)
        .lte("match_date", week_ahead)
        .not_.is_("ft_result", "null")
        .execute()
    )
    played_set = {(r["division"], r["home_team"], r["away_team"]) for r in played_resp.data}
    before = len(upcoming)
    upcoming = upcoming[
        ~upcoming.apply(
            lambda r: (r["division"], r["home_team"], r["away_team"]) in played_set,
            axis=1,
        )
    ]
    ghost_count = before - len(upcoming)
    if ghost_count:
        logger.warning("Filtered out %d ghost fixtures (already played)", ghost_count)

    if upcoming.empty:
        logger.info("No upcoming matches after ghost filtering.")
        return

    logger.info("Found %d upcoming matches", len(upcoming))

    team_features = pd.read_parquet(FEATURES_PATH)
    team_features["match_date"] = pd.to_datetime(team_features["match_date"])

    national_features = load_national_features()
    h2h_stats = load_h2h_features()
    if national_features:
        logger.info("Loaded national team features for %d teams", len(national_features))
    if h2h_stats:
        logger.info("Loaded H2H features for %d pairs", len(h2h_stats))

    wc_played_resp = (
        client.table("matches")
        .select("match_date,home_team,away_team,ft_result,ft_home_goals,ft_away_goals")
        .eq("division", "WC")
        .not_.is_("ft_result", "null")
        .order("match_date")
        .execute()
    )
    wc_played = wc_played_resp.data or []
    logger.info("Loaded %d played WC matches for rest_days calculation", len(wc_played))

    if wc_played and national_features:
        national_features = _update_features_with_wc_results(national_features, wc_played)

    wc_standings = _build_group_standings(wc_played) if wc_played else {}

    predictions = []
    for _, match in upcoming.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        division = match["division"]

        matchday = (
            _compute_matchday(home, away, str(match["match_date"]), wc_played)
            if division == "WC" and wc_played
            else 1
        )

        match_national = national_features
        if division == "WC" and national_features and matchday >= 3:
            match_national = _apply_tournament_form_override(national_features, wc_played, matchday)

        use_national = division == "WC" and match_national
        home_feat = team_features[team_features["team"] == home].sort_values("match_date")
        away_feat = team_features[team_features["team"] == away].sort_values("match_date")

        if use_national or home_feat.empty or away_feat.empty:
            if match_national and (home in match_national or away in match_national):
                feature_row = _build_feature_row_from_national(
                    match_national,
                    home,
                    away,
                    match,
                    h2h_stats=h2h_stats,
                    wc_played=wc_played,
                )
                if not feature_row:
                    logger.warning(
                        "Incomplete national features for %s vs %s, skipping", home, away
                    )
                    continue
                logger.info("Using national team features for %s vs %s", home, away)
            else:
                logger.warning("No features for %s vs %s, skipping", home, away)
                continue
        else:
            latest_home = home_feat.iloc[-1]
            latest_away = away_feat.iloc[-1]

            feature_row = {}
            rolling_cols = [
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
                "venue_win_rate",
                "venue_goals_avg",
                "league_pos",
                "h2h_win_rate",
                "h2h_avg_goals",
                "h2h_matches",
            ]
            for col in rolling_cols:
                feature_row[f"home_{col}"] = latest_home.get(col, float("nan"))
                feature_row[f"away_{col}"] = latest_away.get(col, float("nan"))

            upcoming_date = pd.to_datetime(match["match_date"])
            last_home_date = pd.to_datetime(latest_home.get("match_date"))
            last_away_date = pd.to_datetime(latest_away.get("match_date"))
            home_rest = (upcoming_date - last_home_date).days if pd.notna(last_home_date) else 7
            away_rest = (upcoming_date - last_away_date).days if pd.notna(last_away_date) else 7
            feature_row["home_rest_days"] = home_rest
            feature_row["away_rest_days"] = away_rest

            home_elo = match.get("home_elo") or 1500.0
            away_elo = match.get("away_elo") or 1500.0
            feature_row["home_elo"] = home_elo
            feature_row["away_elo"] = away_elo
            feature_row["elo_diff"] = home_elo - away_elo

            home_lp = feature_row.get("home_league_pos", float("nan"))
            away_lp = feature_row.get("away_league_pos", float("nan"))
            if pd.notna(home_lp) and pd.notna(away_lp):
                feature_row["league_pos_diff"] = home_lp - away_lp
            else:
                feature_row["league_pos_diff"] = float("nan")

        feature_df = pd.DataFrame([feature_row])
        preds = predict_upcoming(feature_df, division)
        preds = _apply_host_boost(preds, home, division)
        preds = _apply_wc_draw_boost(preds, division)

        if match_national and division == "WC":
            poisson_est = _get_poisson_probs(home, away, match_national, division)
            preds = _apply_ensemble(preds, poisson_est, division)

        if division == "WC" and wc_standings:
            preds = _apply_draw_context_boost(preds, home, away, division, wc_standings, matchday)

        home_elo = match.get("home_elo") or 1500.0
        away_elo = match.get("away_elo") or 1500.0
        preds = _apply_draw_zone(preds, division, home_elo - away_elo, home, away)

        # League Poisson ensemble disabled until ELO ratings are stable
        # if division in LEAGUE_DIVISIONS:
        #     league_poisson = get_league_poisson_probs(...)
        #     preds = apply_league_ensemble(preds, league_poisson)
        #     preds = apply_league_draw_zone(preds, ...)

        preds["match_date"] = match["match_date"]
        preds["home_team"] = home
        preds["away_team"] = away
        preds["division"] = division
        predictions.append(preds)

    if national_features:
        elo_updated = 0
        for _, match in upcoming.iterrows():
            h_elo = national_features.get(match["home_team"], {}).get("elo")
            a_elo = national_features.get(match["away_team"], {}).get("elo")
            if h_elo or a_elo:
                update = {}
                if h_elo:
                    update["home_elo"] = round(h_elo, 1)
                if a_elo:
                    update["away_elo"] = round(a_elo, 1)
                client.table("matches").update(update).eq(
                    "match_date", str(match["match_date"])
                ).eq("home_team", match["home_team"]).eq("away_team", match["away_team"]).execute()
                elo_updated += 1
        if elo_updated:
            logger.info("Updated ELO for %d matches from national features", elo_updated)

    if not predictions:
        logger.info("No predictions generated.")
        return

    logger.info("Generated %d predictions, uploading to Supabase...", len(predictions))

    # Delete only predictions for unplayed matches we're about to regenerate
    # Predictions for played matches (with ft_result) are preserved for track record
    for pred in predictions:
        client.table("predictions").delete().eq("match_date", str(pred["match_date"])).eq(
            "home_team", pred["home_team"]
        ).eq("away_team", pred["away_team"]).execute()
    logger.info("Cleared stale predictions for %d upcoming matches", len(predictions))

    for pred in predictions:
        row = {
            "match_date": str(pred["match_date"]),
            "home_team": pred["home_team"],
            "away_team": pred["away_team"],
            "division": pred["division"],
            "model_variant": pred["model_variant"],
            "prob_home": pred.get("prob_home"),
            "prob_draw": pred.get("prob_draw"),
            "prob_away": pred.get("prob_away"),
            "prob_over25": pred.get("prob_over25"),
            "prob_btts": pred.get("prob_btts"),
            "predicted_result": pred.get("predicted_result"),
            "confidence": pred.get("confidence"),
        }
        client.table("predictions").insert(row).execute()

    logger.info("Done! %d predictions uploaded.", len(predictions))


if __name__ == "__main__":
    main()
