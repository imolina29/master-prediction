"""Retrain XGBoost models with international match data and compare WC predictions."""

import csv
import io
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INTL_RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)

DATASET_TO_CANONICAL = {
    "Bosnia and Herzegovina": "Bosnia Herzegovina",
    "Cape Verde": "Cape Verde Islands",
    "DR Congo": "Congo DR",
    "Curaçao": "Curacao",
    "Czech Republic": "Czechia",
    "Korea Republic": "South Korea",
    "Ivory Coast": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "United States": "United States",
    "Korea DPR": "North Korea",
    "China PR": "China",
    "Chinese Taipei": "Taiwan",
    "Trinidad and Tobago": "Trinidad & Tobago",
    "Antigua and Barbuda": "Antigua & Barbuda",
    "Saint Kitts and Nevis": "St Kitts & Nevis",
    "Saint Lucia": "St Lucia",
    "Saint Vincent and the Grenadines": "St Vincent & Grenadines",
    "São Tomé and Príncipe": "Sao Tome & Principe",
    "Turks and Caicos Islands": "Turks & Caicos",
}


def _normalize_name(name: str) -> str:
    return DATASET_TO_CANONICAL.get(name, name)


def download_international_matches(min_date: str = "2018-01-01") -> pd.DataFrame:
    from backend.etl.http import get_with_retry

    logger.info("Downloading international results...")
    resp = get_with_retry(INTL_RESULTS_URL, timeout=60)
    reader = csv.DictReader(io.StringIO(resp.text))

    matches = []
    for row in reader:
        if row["date"] < min_date:
            continue
        if row["home_score"] == "NA" or row["away_score"] == "NA":
            continue

        home_goals = int(row["home_score"])
        away_goals = int(row["away_score"])

        if home_goals > away_goals:
            result = "H"
        elif away_goals > home_goals:
            result = "A"
        else:
            result = "D"

        matches.append(
            {
                "division": "INTL",
                "match_date": row["date"],
                "home_team": _normalize_name(row["home_team"]),
                "away_team": _normalize_name(row["away_team"]),
                "ft_home_goals": home_goals,
                "ft_away_goals": away_goals,
                "ft_result": result,
                "tournament": row.get("tournament", ""),
                "neutral": row.get("neutral", "FALSE") == "TRUE",
            }
        )

    df = pd.DataFrame(matches)
    df["match_date"] = pd.to_datetime(df["match_date"])
    logger.info("Filtered to %d international matches since %s", len(df), min_date)
    return df


def _rolling_avg(values: list[float], n: int) -> float:
    window = values[-n:]
    return sum(window) / len(window) if window else float("nan")


def build_intl_match_features(intl_df: pd.DataFrame) -> pd.DataFrame:
    """Build match-level features directly from international results.

    Computes rolling stats, progressive ELO, rest days, and venue stats
    for each match, producing one row per match with all BASE_FEATURES columns.
    """
    intl_df = intl_df.sort_values("match_date").reset_index(drop=True)

    team_history: dict[str, list[dict]] = {}
    team_venue_history: dict[str, dict[str, list[dict]]] = {}
    elo: dict[str, float] = {}
    k_factor = 40

    match_rows = []

    for _, row in intl_df.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        hg = row["ft_home_goals"]
        ag = row["ft_away_goals"]

        if home not in team_history:
            team_history[home] = []
            team_venue_history[home] = {"home": [], "away": []}
        if away not in team_history:
            team_history[away] = []
            team_venue_history[away] = {"home": [], "away": []}
        if home not in elo:
            elo[home] = 1500.0
        if away not in elo:
            elo[away] = 1500.0

        home_matches = team_history[home]
        away_matches = team_history[away]

        if len(home_matches) < 3 or len(away_matches) < 3:
            _record_match(
                team_history,
                team_venue_history,
                home,
                away,
                hg,
                ag,
                row["match_date"],
            )
            _update_elo(elo, home, away, hg, ag, k_factor)
            continue

        feature_row = {}

        for prefix, matches, venue_h in [
            ("home", home_matches, team_venue_history[home]["home"]),
            ("away", away_matches, team_venue_history[away]["away"]),
        ]:
            recent5 = matches[-5:]
            n = len(recent5)
            gf = [m["gf"] for m in recent5]
            ga = [m["ga"] for m in recent5]
            wins = [1.0 if m["gf"] > m["ga"] else 0.0 for m in recent5]
            draws = [1.0 if m["gf"] == m["ga"] else 0.0 for m in recent5]
            btts = [1.0 if m["gf"] > 0 and m["ga"] > 0 else 0.0 for m in recent5]
            over25 = [1.0 if m["gf"] + m["ga"] > 2 else 0.0 for m in recent5]

            feature_row[f"{prefix}_goals_scored_avg"] = sum(gf) / n
            feature_row[f"{prefix}_goals_conceded_avg"] = sum(ga) / n
            feature_row[f"{prefix}_shots_target_avg"] = float("nan")
            feature_row[f"{prefix}_corners_avg"] = float("nan")
            feature_row[f"{prefix}_win_rate"] = sum(wins) / n
            feature_row[f"{prefix}_draw_rate"] = sum(draws) / n
            feature_row[f"{prefix}_btts_rate"] = sum(btts) / n
            feature_row[f"{prefix}_over25_rate"] = sum(over25) / n

            all_gf = [m["gf"] for m in matches]
            all_ga = [m["ga"] for m in matches]
            all_wins = [1.0 if m["gf"] > m["ga"] else 0.0 for m in matches]

            feature_row[f"{prefix}_goals_scored_avg_3"] = _rolling_avg(all_gf, 3)
            feature_row[f"{prefix}_goals_conceded_avg_3"] = _rolling_avg(all_ga, 3)
            feature_row[f"{prefix}_win_rate_3"] = _rolling_avg(all_wins, 3)
            feature_row[f"{prefix}_goals_scored_avg_10"] = _rolling_avg(all_gf, 10)
            feature_row[f"{prefix}_goals_conceded_avg_10"] = _rolling_avg(all_ga, 10)
            feature_row[f"{prefix}_win_rate_10"] = _rolling_avg(all_wins, 10)

            feature_row[f"{prefix}_xg_for_avg"] = float("nan")
            feature_row[f"{prefix}_xg_against_avg"] = float("nan")
            feature_row[f"{prefix}_xg_diff_avg"] = float("nan")
            feature_row[f"{prefix}_xg_overperformance"] = float("nan")

            if venue_h:
                v_recent = venue_h[-5:]
                v_wins = sum(1 for m in v_recent if m["gf"] > m["ga"])
                feature_row[f"{prefix}_venue_win_rate"] = v_wins / len(v_recent)
                feature_row[f"{prefix}_venue_goals_avg"] = (
                    sum(m["gf"] for m in v_recent) / len(v_recent)
                )
            else:
                feature_row[f"{prefix}_venue_win_rate"] = float("nan")
                feature_row[f"{prefix}_venue_goals_avg"] = float("nan")

            last_date = matches[-1]["date"]
            rest = (row["match_date"] - last_date).days
            feature_row[f"{prefix}_rest_days"] = min(rest, 90)

            feature_row[f"{prefix}_league_pos"] = float("nan")
            feature_row[f"{prefix}_h2h_win_rate"] = float("nan")
            feature_row[f"{prefix}_h2h_avg_goals"] = float("nan")
            feature_row[f"{prefix}_h2h_matches"] = float("nan")

        feature_row["home_elo"] = elo[home]
        feature_row["away_elo"] = elo[away]
        feature_row["elo_diff"] = elo[home] - elo[away]
        feature_row["league_pos_diff"] = float("nan")

        feature_row["match_date"] = row["match_date"]
        feature_row["home_team"] = home
        feature_row["away_team"] = away
        feature_row["division"] = "INTL"
        feature_row["ft_home_goals"] = hg
        feature_row["ft_away_goals"] = ag
        feature_row["ft_result"] = row["ft_result"]

        if hg > ag:
            feature_row["target_1x2"] = 0
        elif hg == ag:
            feature_row["target_1x2"] = 1
        else:
            feature_row["target_1x2"] = 2
        feature_row["target_over25"] = int(hg + ag > 2.5)
        feature_row["target_btts"] = int(hg > 0 and ag > 0)

        match_rows.append(feature_row)

        _record_match(
            team_history, team_venue_history, home, away, hg, ag, row["match_date"]
        )
        _update_elo(elo, home, away, hg, ag, k_factor)

    df = pd.DataFrame(match_rows)
    logger.info("Built %d international match feature rows", len(df))
    return df


def _record_match(
    team_history: dict,
    venue_history: dict,
    home: str,
    away: str,
    hg: int,
    ag: int,
    date,
):
    team_history[home].append({"gf": hg, "ga": ag, "date": date})
    team_history[away].append({"gf": ag, "ga": hg, "date": date})
    venue_history[home]["home"].append({"gf": hg, "ga": ag, "date": date})
    venue_history[away]["away"].append({"gf": ag, "ga": hg, "date": date})


def _update_elo(elo: dict, home: str, away: str, hg: int, ag: int, k: float):
    exp_home = 1.0 / (1.0 + 10 ** ((elo[away] - elo[home]) / 400))
    if hg > ag:
        score = 1.0
    elif hg == ag:
        score = 0.5
    else:
        score = 0.0
    delta = k * (score - exp_home)
    elo[home] += delta
    elo[away] -= delta


def generate_wc_predictions(models_dir=None):
    from backend.etl.fixtures import load_national_features
    from backend.ml.predict import _model_cache, predict_upcoming
    from scripts.run_predictions import _build_feature_row_from_national

    _model_cache.clear()

    import os

    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv()
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    today = datetime.now().strftime("%Y-%m-%d")
    week_ahead = (datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d")

    resp = (
        client.table("matches")
        .select("*")
        .gte("match_date", today)
        .lte("match_date", week_ahead)
        .eq("division", "WC")
        .is_("ft_result", "null")
        .execute()
    )
    upcoming = pd.DataFrame(resp.data)

    if upcoming.empty:
        logger.info("No upcoming WC matches found.")
        return []

    national_features = load_national_features()

    predictions = []
    for _, match in upcoming.iterrows():
        home = match["home_team"]
        away = match["away_team"]

        feature_row = _build_feature_row_from_national(
            national_features, home, away, match
        )
        if not feature_row:
            logger.warning("No features for %s vs %s", home, away)
            continue

        feature_df = pd.DataFrame([feature_row])
        preds = predict_upcoming(feature_df, "WC", models_dir)
        preds["match_date"] = match["match_date"]
        preds["home_team"] = home
        preds["away_team"] = away
        predictions.append(preds)

    return predictions


def print_comparison(baseline: list[dict], new_predictions: list[dict]):
    baseline_map = {}
    for p in baseline:
        key = (p["match_date"], p["home_team"], p["away_team"])
        baseline_map[key] = p

    print("\n" + "=" * 130)
    print(
        "COMPARATIVA PREDICCIONES WC: ANTES vs DESPUÉS (con datos internacionales)"
    )
    print("=" * 130)
    header = (
        f"{'Partido':<40} "
        f"{'--- ANTES ---':^28} "
        f"{'--- DESPUÉS ---':^28} "
        f"{'ΔHome':>6}"
    )
    print(header)
    sub = (
        f"{'':40} "
        f"{'H%':>7} {'D%':>7} {'A%':>7} {'Conf':>5} "
        f"{'H%':>7} {'D%':>7} {'A%':>7} {'Conf':>5}"
    )
    print(sub)
    print("-" * 130)

    improved = 0
    total = 0

    for new in sorted(new_predictions, key=lambda x: x["match_date"]):
        key = (new["match_date"], new["home_team"], new["away_team"])
        old = baseline_map.get(key, {})

        match_label = f"{new['home_team']} vs {new['away_team']}"
        if len(match_label) > 38:
            match_label = match_label[:38]

        old_h = (old.get("prob_home") or 0) * 100
        old_d = (old.get("prob_draw") or 0) * 100
        old_a = (old.get("prob_away") or 0) * 100
        old_conf = old.get("confidence", "-")

        new_h = (new.get("prob_home") or 0) * 100
        new_d = (new.get("prob_draw") or 0) * 100
        new_a = (new.get("prob_away") or 0) * 100
        new_conf = new.get("confidence", "-")

        delta = new_h - old_h

        print(
            f"{match_label:<40} "
            f"{old_h:>6.1f}% {old_d:>6.1f}% {old_a:>6.1f}% {old_conf:>5} "
            f"{new_h:>6.1f}% {new_d:>6.1f}% {new_a:>6.1f}% {new_conf:>5} "
            f"{delta:>+6.1f}%"
        )

        total += 1
        if abs(delta) > 1.0:
            improved += 1

    print("=" * 130)
    print(f"\nPartidos con cambio >1%: {improved}/{total}")


def main():
    import os

    from dotenv import load_dotenv
    from supabase import create_client

    from backend.db.helpers import fetch_all
    from backend.ml.config import BASE_FEATURES, FEATURES_PATH, PREMIUM_FEATURES
    from backend.ml.features import build_match_features
    from backend.ml.train import train_all

    load_dotenv()

    # ── Step 1: Load baseline ──
    logger.info("=" * 60)
    logger.info("STEP 1: Loading baseline WC predictions")
    logger.info("=" * 60)
    baseline_path = PROJECT_ROOT / "data" / "baseline_wc_predictions.json"
    with open(baseline_path) as f:
        baseline = json.load(f)
    logger.info("Loaded %d baseline predictions", len(baseline))

    # ── Step 2: Load club training data ──
    logger.info("=" * 60)
    logger.info("STEP 2: Loading club training data")
    logger.info("=" * 60)
    team_features = pd.read_parquet(FEATURES_PATH)
    logger.info("Loaded %d club team-feature rows", len(team_features))

    client = create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
    )
    matches = pd.DataFrame(fetch_all(client, "matches"))
    logger.info("Loaded %d matches from Supabase", len(matches))

    club_matches = matches[matches["division"] != "WC"].copy()
    logger.info("Building club match-level features...")
    club_match_df = build_match_features(team_features, club_matches)
    logger.info("Built %d club match rows", len(club_match_df))

    # ── Step 3: Download and process international data ──
    logger.info("=" * 60)
    logger.info("STEP 3: Processing international match data")
    logger.info("=" * 60)
    intl_df = download_international_matches(min_date="2018-01-01")
    intl_match_df = build_intl_match_features(intl_df)
    logger.info("International data ready: %d match rows", len(intl_match_df))

    # ── Step 4: Combine and retrain ──
    logger.info("=" * 60)
    logger.info("STEP 4: Combining data and retraining models")
    logger.info("=" * 60)

    models_dir = PROJECT_ROOT / "models"
    backup_dir = PROJECT_ROOT / "models_backup"
    if not backup_dir.exists():
        shutil.copytree(models_dir, backup_dir)
        logger.info("Backed up current models to %s", backup_dir)

    for col in club_match_df.columns:
        if col not in intl_match_df.columns:
            intl_match_df[col] = float("nan")
    for col in intl_match_df.columns:
        if col not in club_match_df.columns:
            club_match_df[col] = float("nan")

    combined = pd.concat([club_match_df, intl_match_df], ignore_index=True)
    combined.sort_values("match_date", inplace=True)
    logger.info(
        "Combined: %d total rows (%d club + %d intl)",
        len(combined),
        len(club_match_df),
        len(intl_match_df),
    )

    has_xg = combined["home_xg_for_avg"].notna() & combined["away_xg_for_avg"].notna()
    premium_df = combined[has_xg].copy()
    base_df = combined.copy()
    logger.info("Base: %d rows, Premium: %d rows", len(base_df), len(premium_df))

    logger.info("Training all 6 models...")
    train_all(base_df, premium_df)
    logger.info("Models retrained!")

    # ── Step 5: Generate new predictions and compare ──
    logger.info("=" * 60)
    logger.info("STEP 5: Generating new WC predictions")
    logger.info("=" * 60)
    new_predictions = generate_wc_predictions()

    if new_predictions:
        print_comparison(baseline, new_predictions)
    else:
        logger.warning("No new WC predictions generated")

    new_path = PROJECT_ROOT / "data" / "new_wc_predictions.json"
    with open(new_path, "w") as f:
        json.dump(new_predictions, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Saved new predictions to %s", new_path)


if __name__ == "__main__":
    main()
