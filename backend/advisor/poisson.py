"""Poisson-based score estimation for football matches.

Uses team goal averages + ELO ratings to estimate expected goals (lambda),
then computes a probability matrix for all possible scorelines.
Applies Dixon-Coles correction for low-scoring outcomes.
"""

import math


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam**k) * math.exp(-lam) / math.factorial(k)


def _dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    lambda_away: float,
    rho: float,
) -> float:
    """Correction factor for low-scoring outcomes (Dixon & Coles, 1997)."""
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lambda_home * lambda_away * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + lambda_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lambda_home * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def estimate_score(
    home_attack: float,
    home_defense: float,
    away_attack: float,
    away_defense: float,
    home_elo: float = 1500.0,
    away_elo: float = 1500.0,
    global_avg: float = 1.3,
    home_advantage: float = 1.0,
    rho: float = -0.13,
    max_goals: int = 6,
) -> dict:
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
            p = _poisson_pmf(i, lambda_home) * _poisson_pmf(j, lambda_away)
            tau = _dixon_coles_tau(i, j, lambda_home, lambda_away, rho)
            matrix[(i, j)] = max(p * tau, 0.0)

    total_mass = sum(matrix.values())
    if total_mass > 0:
        matrix = {k: v / total_mass for k, v in matrix.items()}

    sorted_scores = sorted(matrix.items(), key=lambda x: x[1], reverse=True)

    return {
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "top_scores": [(f"{h}-{a}", round(p, 4)) for (h, a), p in sorted_scores[:5]],
        "prob_home": round(sum(p for (h, a), p in matrix.items() if h > a), 4),
        "prob_draw": round(sum(p for (h, a), p in matrix.items() if h == a), 4),
        "prob_away": round(sum(p for (h, a), p in matrix.items() if h < a), 4),
        "prob_over25": round(sum(p for (h, a), p in matrix.items() if h + a > 2), 4),
        "prob_btts": round(sum(p for (h, a), p in matrix.items() if h > 0 and a > 0), 4),
    }
