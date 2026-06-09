"""Poisson-based score estimation for football matches.

Uses team goal averages + ELO ratings to estimate expected goals (lambda),
then computes a probability matrix for all possible scorelines.
"""

import math


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam**k) * math.exp(-lam) / math.factorial(k)


def estimate_score(
    home_attack: float,
    home_defense: float,
    away_attack: float,
    away_defense: float,
    home_elo: float = 1500.0,
    away_elo: float = 1500.0,
    global_avg: float = 1.3,
    home_advantage: float = 1.0,
    max_goals: int = 6,
) -> dict:
    """Estimate match score probabilities using Poisson distribution.

    lambda_home = (home_attack * away_defense / global_avg) * home_advantage
    lambda_away = away_attack * home_defense / global_avg

    ELO adjustment scales lambdas to account for opponent strength.
    """
    lambda_home = (home_attack * away_defense / global_avg) * home_advantage
    lambda_away = away_attack * home_defense / global_avg

    elo_diff = home_elo - away_elo
    e_home = 1 / (1 + 10 ** (-elo_diff / 400))
    ratio = e_home / max(1 - e_home, 0.05)
    elo_factor = ratio**0.18
    lambda_home *= elo_factor
    lambda_away /= elo_factor

    lambda_home = max(0.3, min(4.5, lambda_home))
    lambda_away = max(0.3, min(4.5, lambda_away))

    matrix = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            matrix[(i, j)] = _poisson_pmf(i, lambda_home) * _poisson_pmf(j, lambda_away)

    sorted_scores = sorted(matrix.items(), key=lambda x: x[1], reverse=True)

    return {
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "top_scores": [(f"{h}-{a}", round(p, 4)) for (h, a), p in sorted_scores[:5]],
        "prob_home": round(sum(p for (h, a), p in matrix.items() if h > a), 3),
        "prob_draw": round(sum(p for (h, a), p in matrix.items() if h == a), 3),
        "prob_away": round(sum(p for (h, a), p in matrix.items() if h < a), 3),
        "prob_over25": round(sum(p for (h, a), p in matrix.items() if h + a > 2), 3),
        "prob_btts": round(sum(p for (h, a), p in matrix.items() if h > 0 and a > 0), 3),
    }
