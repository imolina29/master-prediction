"""ELO rating system for league teams using historical match data."""

import logging

logger = logging.getLogger(__name__)

K_FACTOR = 32
HOME_ADVANTAGE = 50
DEFAULT_ELO = 1500.0


def compute_league_elo(matches: list[dict]) -> dict[str, float]:
    """Compute ELO ratings from chronologically sorted finished matches.

    Args:
        matches: list of dicts with keys: home_team, away_team, ft_result.
                 Must be sorted by match_date ascending.

    Returns:
        dict mapping team name -> current ELO rating.
    """
    elo: dict[str, float] = {}

    for m in matches:
        home = m["home_team"]
        away = m["away_team"]
        result = m.get("ft_result")

        if not result:
            continue

        if home not in elo:
            elo[home] = DEFAULT_ELO
        if away not in elo:
            elo[away] = DEFAULT_ELO

        home_r = elo[home] + HOME_ADVANTAGE
        away_r = elo[away]

        exp_home = 1.0 / (1.0 + 10 ** ((away_r - home_r) / 400))

        if result == "H":
            score_home = 1.0
        elif result == "D":
            score_home = 0.5
        else:
            score_home = 0.0

        delta = K_FACTOR * (score_home - exp_home)
        elo[home] += delta
        elo[away] -= delta

    return {team: round(rating, 1) for team, rating in elo.items()}


def get_team_elo(elo_ratings: dict[str, float], team: str) -> float:
    return elo_ratings.get(team, DEFAULT_ELO)
