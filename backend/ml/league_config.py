"""Per-league constants for post-processing predictions."""

LEAGUE_DIVISIONS = {"E0", "SP1", "D1", "I1", "F1", "EC"}

LEAGUE_HOME_ADVANTAGE = {
    "E0": 1.15,
    "SP1": 1.15,
    "D1": 1.12,
    "I1": 1.18,
    "F1": 1.15,
    "EC": 1.0,
}

LEAGUE_GLOBAL_AVG = {
    "E0": 1.35,
    "SP1": 1.25,
    "D1": 1.40,
    "I1": 1.25,
    "F1": 1.30,
    "EC": 1.30,
}

LEAGUE_ENSEMBLE_XGB = 0.70
LEAGUE_ENSEMBLE_POISSON = 0.30

LEAGUE_TIGHT_MARGIN = 0.05
LEAGUE_DRAW_ZONE_THRESHOLD = 0.28
LEAGUE_DRAW_ZONE_SPREAD = 0.12
LEAGUE_DRAW_ZONE_ELO_MAX = 80
