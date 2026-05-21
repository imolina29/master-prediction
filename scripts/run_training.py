import json
import logging

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from backend.ml.config import (
        BACKTEST_RESULTS_PATH,
        BASE_FEATURES,
        FEATURES_PATH,
        MODELS_DIR,
        PREMIUM_FEATURES,
        TARGETS,
    )
    from backend.ml.evaluate import walk_forward_backtest
    from backend.ml.features import build_match_features
    from backend.ml.train import train_all

    logger.info("Loading team features from %s", FEATURES_PATH)
    team_features = pd.read_parquet(FEATURES_PATH)
    logger.info("Loaded %d team-feature rows", len(team_features))

    from backend.db.client import get_supabase

    client = get_supabase()
    all_data: list[dict] = []
    offset = 0
    page_size = 1000
    while True:
        resp = (
            client.table("matches")
            .select("*")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_data.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    matches = pd.DataFrame(all_data)
    logger.info("Loaded %d matches from Supabase", len(matches))

    logger.info("Building match-level features...")
    match_df = build_match_features(team_features, matches)
    logger.info("Built %d match rows", len(match_df))

    has_xg = match_df["home_xg_for_avg"].notna() & match_df["away_xg_for_avg"].notna()
    premium_df = match_df[has_xg].copy()
    base_df = match_df.copy()
    logger.info("Base: %d rows, Premium: %d rows", len(base_df), len(premium_df))

    logger.info("Training all 6 models...")
    train_all(base_df, premium_df)
    logger.info("Models saved to %s", MODELS_DIR)

    logger.info("Running walk-forward backtesting...")
    for target in TARGETS:
        walk_forward_backtest(
            base_df, target, "base", BASE_FEATURES, output_path=BACKTEST_RESULTS_PATH
        )
        if len(premium_df) > 100:
            walk_forward_backtest(
                premium_df,
                target,
                "premium",
                PREMIUM_FEATURES,
                output_path=BACKTEST_RESULTS_PATH,
            )

    logger.info("Backtest results saved to %s", BACKTEST_RESULTS_PATH)
    with open(BACKTEST_RESULTS_PATH) as f:
        results = json.load(f)
    for model_name, data in results.items():
        acc = data.get("mean_accuracy", "N/A")
        roi = data.get("mean_roi_pct", "N/A")
        logger.info("  %s — accuracy: %s, ROI: %s%%", model_name, acc, roi)


if __name__ == "__main__":
    main()
