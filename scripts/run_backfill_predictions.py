"""Backfill predictions for already-played matches.

Regenerates predictions for matches that have results but no
corresponding prediction row (e.g. after an accidental cleanup).
Uses the current model & features — predictions are approximate
since features include data from after the match, but the rolling
averages make the difference negligible.

Usage:
    PYTHONPATH=. python scripts/run_backfill_predictions.py [--since 2026-08-01]
"""

import argparse
import logging
from datetime import date

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--since",
        default="2026-08-01",
        help="Backfill from this date (default: 2026-08-01)",
    )
    args = parser.parse_args()

    from backend.db.client import get_supabase
    from backend.ml.config import FEATURES_PATH
    from backend.ml.predict import predict_upcoming

    client = get_supabase()
    today = date.today().isoformat()

    # 1. Get played matches in the window
    played_resp = (
        client.table("matches")
        .select("*")
        .gte("match_date", args.since)
        .lt("match_date", today)
        .not_.is_("ft_result", "null")
        .order("match_date")
        .execute()
    )
    played = pd.DataFrame(played_resp.data)
    if played.empty:
        logger.info("No played matches found since %s", args.since)
        return

    logger.info("Found %d played matches since %s", len(played), args.since)

    # 2. Get existing predictions so we skip matches that already have one
    existing_resp = (
        client.table("predictions")
        .select("match_date,home_team,away_team")
        .gte("match_date", args.since)
        .lt("match_date", today)
        .execute()
    )
    existing_keys = {(r["match_date"], r["home_team"], r["away_team"]) for r in existing_resp.data}
    logger.info("Found %d existing past predictions", len(existing_keys))

    # 3. Filter to only matches missing predictions
    missing = played[
        ~played.apply(
            lambda r: (
                (
                    r["match_date"],
                    r["home_team"],
                    r["away_team"],
                )
                in existing_keys
            ),
            axis=1,
        )
    ]
    if missing.empty:
        logger.info("All played matches already have predictions.")
        return

    logger.info("%d matches need backfill predictions", len(missing))

    # 4. Load features
    team_features = pd.read_parquet(FEATURES_PATH)
    team_features["match_date"] = pd.to_datetime(team_features["match_date"])

    # 5. Generate predictions for each match
    generated = 0
    skipped = 0
    for _, match in missing.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        division = match["division"]

        home_feat = team_features[team_features["team"] == home].sort_values("match_date")
        away_feat = team_features[team_features["team"] == away].sort_values("match_date")

        if home_feat.empty or away_feat.empty:
            skipped += 1
            continue

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

        row = {
            "match_date": str(match["match_date"]),
            "home_team": home,
            "away_team": away,
            "division": division,
            "model_variant": preds["model_variant"],
            "prob_home": preds.get("prob_home"),
            "prob_draw": preds.get("prob_draw"),
            "prob_away": preds.get("prob_away"),
            "prob_over25": preds.get("prob_over25"),
            "prob_btts": preds.get("prob_btts"),
            "predicted_result": preds.get("predicted_result"),
            "confidence": preds.get("confidence"),
        }
        client.table("predictions").insert(row).execute()
        generated += 1

    logger.info(
        "Backfill complete: %d generated, %d skipped (no features)",
        generated,
        skipped,
    )


if __name__ == "__main__":
    main()
