import csv
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

TARGET_DIVISIONS = {"E0", "E1", "SP1", "SP2", "I1", "I2", "D1", "D2", "F1", "F2", "EC"}

CSV_TO_FIELD = {
    "Division": "division",
    "MatchDate": "match_date",
    "MatchTime": "match_time",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "HomeElo": "home_elo",
    "AwayElo": "away_elo",
    "Form3Home": "home_form3",
    "Form5Home": "home_form5",
    "Form3Away": "away_form3",
    "Form5Away": "away_form5",
    "FTHome": "ft_home_goals",
    "FTAway": "ft_away_goals",
    "FTResult": "ft_result",
    "HTHome": "ht_home_goals",
    "HTAway": "ht_away_goals",
    "HTResult": "ht_result",
    "HomeShots": "home_shots",
    "AwayShots": "away_shots",
    "HomeTarget": "home_shots_target",
    "AwayTarget": "away_shots_target",
    "HomeFouls": "home_fouls",
    "AwayFouls": "away_fouls",
    "HomeCorners": "home_corners",
    "AwayCorners": "away_corners",
    "HomeYellow": "home_yellow",
    "AwayYellow": "away_yellow",
    "HomeRed": "home_red",
    "AwayRed": "away_red",
    "OddHome": "odd_home",
    "OddDraw": "odd_draw",
    "OddAway": "odd_away",
    "MaxHome": "odd_max_home",
    "MaxDraw": "odd_max_draw",
    "MaxAway": "odd_max_away",
    "Over25": "odd_over25",
    "Under25": "odd_under25",
    "MaxOver25": "odd_max_over25",
    "MaxUnder25": "odd_max_under25",
    "HandiSize": "odd_handi_size",
    "HandiHome": "odd_handi_home",
    "HandiAway": "odd_handi_away",
}

TEXT_FIELDS = {
    "division",
    "match_date",
    "match_time",
    "home_team",
    "away_team",
    "ft_result",
    "ht_result",
}
INT_FIELDS = {
    "ft_home_goals",
    "ft_away_goals",
    "ht_home_goals",
    "ht_away_goals",
    "home_shots",
    "away_shots",
    "home_shots_target",
    "away_shots_target",
    "home_fouls",
    "away_fouls",
    "home_corners",
    "away_corners",
    "home_yellow",
    "away_yellow",
    "home_red",
    "away_red",
}


@dataclass
class MatchRow:
    division: str
    match_date: str
    match_time: str | None
    home_team: str
    away_team: str
    home_elo: float | None
    away_elo: float | None
    home_form3: float | None
    home_form5: float | None
    away_form3: float | None
    away_form5: float | None
    ft_home_goals: int | None
    ft_away_goals: int | None
    ft_result: str | None
    ht_home_goals: int | None
    ht_away_goals: int | None
    ht_result: str | None
    home_shots: int | None
    away_shots: int | None
    home_shots_target: int | None
    away_shots_target: int | None
    home_fouls: int | None
    away_fouls: int | None
    home_corners: int | None
    away_corners: int | None
    home_yellow: int | None
    away_yellow: int | None
    home_red: int | None
    away_red: int | None
    odd_home: float | None
    odd_draw: float | None
    odd_away: float | None
    odd_max_home: float | None
    odd_max_draw: float | None
    odd_max_away: float | None
    odd_over25: float | None
    odd_under25: float | None
    odd_max_over25: float | None
    odd_max_under25: float | None
    odd_handi_size: float | None
    odd_handi_home: float | None
    odd_handi_away: float | None


def _parse_value(raw: str, field: str) -> str | int | float | None:
    stripped = raw.strip()
    if not stripped:
        return None
    if field in TEXT_FIELDS:
        return stripped
    if field in INT_FIELDS:
        return int(float(stripped))
    return float(stripped)


def parse_matches_csv(
    path: Path,
    divisions: set[str] | None = None,
) -> list[MatchRow]:
    if divisions is None:
        divisions = TARGET_DIVISIONS

    rows: list[MatchRow] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            div = raw_row.get("Division", "").strip()
            if div not in divisions:
                continue

            parsed = {}
            for csv_col, field_name in CSV_TO_FIELD.items():
                raw_val = raw_row.get(csv_col, "")
                parsed[field_name] = _parse_value(raw_val, field_name)

            if not parsed.get("match_date") or not parsed.get("home_team"):
                continue

            rows.append(MatchRow(**parsed))

    logger.info("Parsed %d matches from %s (filtered to %s)", len(rows), path.name, divisions)
    return rows
