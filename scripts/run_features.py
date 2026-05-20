import logging

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    from backend.db.client import get_supabase
    from backend.services.features import compute_team_features, save_features

    client = get_supabase()

    logging.info("Loading matches from Supabase...")
    matches_resp = client.table("matches").select("*").execute()
    matches_df = pd.DataFrame(matches_resp.data)
    logging.info("Loaded %d matches", len(matches_df))

    logging.info("Loading xG data from Supabase...")
    xg_resp = client.table("match_xg").select("*").execute()
    xg_df = pd.DataFrame(xg_resp.data)
    logging.info("Loaded %d xG records", len(xg_df))

    if not xg_df.empty:
        matches_df = matches_df.merge(
            xg_df[["division", "match_date", "home_team", "away_team", "home_xg", "away_xg"]],
            on=["division", "match_date", "home_team", "away_team"],
            how="left",
        )
    else:
        matches_df["home_xg"] = None
        matches_df["away_xg"] = None

    features = compute_team_features(matches_df, window=5)
    path = save_features(features)
    logging.info("Features saved to %s (%d rows)", path, len(features))


if __name__ == "__main__":
    main()
