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
    preds["predicted_result"] = ["H", "D", "A"][int(np.argmax(probs))]
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
    preds["predicted_result"] = ["H", "D", "A"][int(np.argmax(probs))]
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

    preds["predicted_result"] = ["H", "D", "A"][int(np.argmax(probs))]

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

    predictions = []
    for _, match in upcoming.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        division = match["division"]

        use_national = division == "WC" and national_features
        home_feat = team_features[team_features["team"] == home].sort_values("match_date")
        away_feat = team_features[team_features["team"] == away].sort_values("match_date")

        if use_national or home_feat.empty or away_feat.empty:
            if national_features and (home in national_features or away in national_features):
                feature_row = _build_feature_row_from_national(
                    national_features,
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

        if national_features and division == "WC":
            poisson_est = _get_poisson_probs(home, away, national_features, division)
            preds = _apply_ensemble(preds, poisson_est, division)

        home_elo = match.get("home_elo") or 1500.0
        away_elo = match.get("away_elo") or 1500.0
        preds = _apply_draw_zone(preds, division, home_elo - away_elo, home, away)

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

    # Only delete predictions for matches we're about to regenerate (preserves played match data)
    for _, match in upcoming.iterrows():
        client.table("predictions").delete().eq("match_date", str(match["match_date"])).eq(
            "home_team", match["home_team"]
        ).eq("away_team", match["away_team"]).execute()
    logger.info("Cleared stale predictions for %d upcoming matches", len(upcoming))

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
