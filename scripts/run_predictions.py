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
    from backend.ml.predict import classify_confidence

    preds["confidence"] = classify_confidence(max(probs))
    logger.info("Applied host boost for %s: H=%.0f%%", home, preds["prob_home"] * 100)
    return preds


def _build_feature_row_from_national(features: dict, home: str, away: str, match: dict) -> dict:
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

    for col in [
        "rest_days",
        "venue_win_rate",
        "venue_goals_avg",
        "league_pos",
        "h2h_win_rate",
        "h2h_avg_goals",
        "h2h_matches",
    ]:
        feature_row[f"home_{col}"] = float("nan")
        feature_row[f"away_{col}"] = float("nan")
    feature_row["league_pos_diff"] = float("nan")

    return feature_row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upcoming", action="store_true", help="Predict upcoming 7 days")
    parser.parse_args()

    from backend.db.client import get_supabase
    from backend.etl.fixtures import load_national_features
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
    if national_features:
        logger.info("Loaded national team features for %d teams", len(national_features))

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
                feature_row = _build_feature_row_from_national(national_features, home, away, match)
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

        preds["match_date"] = match["match_date"]
        preds["home_team"] = home
        preds["away_team"] = away
        preds["division"] = division
        predictions.append(preds)

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
