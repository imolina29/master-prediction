import argparse
import logging
from datetime import datetime, timedelta

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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
    ]
    for col in rolling_cols:
        feature_row[f"home_{col}"] = home_feat.get(col)
        feature_row[f"away_{col}"] = away_feat.get(col)

    for col in ["xg_for_avg", "xg_against_avg", "xg_diff_avg", "xg_overperformance"]:
        feature_row[f"home_{col}"] = float("nan")
        feature_row[f"away_{col}"] = float("nan")

    home_elo = match.get("home_elo") or 1500.0
    away_elo = match.get("away_elo") or 1500.0
    feature_row["home_elo"] = home_elo
    feature_row["away_elo"] = away_elo
    feature_row["elo_diff"] = home_elo - away_elo
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

    today = datetime.now().strftime("%Y-%m-%d")
    week_ahead = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

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

        home_feat = team_features[team_features["team"] == home].sort_values("match_date")
        away_feat = team_features[team_features["team"] == away].sort_values("match_date")

        if home_feat.empty or away_feat.empty:
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
            ]
            for col in rolling_cols:
                feature_row[f"home_{col}"] = latest_home.get(col, float("nan"))
                feature_row[f"away_{col}"] = latest_away.get(col, float("nan"))

            home_elo = match.get("home_elo") or 1500.0
            away_elo = match.get("away_elo") or 1500.0
            feature_row["home_elo"] = home_elo
            feature_row["away_elo"] = away_elo
            feature_row["elo_diff"] = home_elo - away_elo

        feature_df = pd.DataFrame([feature_row])
        preds = predict_upcoming(feature_df, division)

        preds["match_date"] = match["match_date"]
        preds["home_team"] = home
        preds["away_team"] = away
        preds["division"] = division
        predictions.append(preds)

    if not predictions:
        logger.info("No predictions generated.")
        return

    logger.info("Generated %d predictions, uploading to Supabase...", len(predictions))
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
        client.table("predictions").upsert(
            row, on_conflict="match_date,home_team,away_team"
        ).execute()

    logger.info("Done! %d predictions uploaded.", len(predictions))


if __name__ == "__main__":
    main()
