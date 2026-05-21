from backend.betting.value import calculate_edge, classify_stake, generate_picks


def test_calculate_edge_positive():
    result = calculate_edge(0.55, 2.10)
    assert round(result["implied_prob"], 4) == round(1 / 2.10, 4)
    assert round(result["edge"], 4) == round(0.55 - 1 / 2.10, 4)
    assert round(result["expected_value"], 4) == round((0.55 * 2.10) - 1, 4)


def test_calculate_edge_negative():
    result = calculate_edge(0.30, 2.10)
    assert result["edge"] < 0


def test_classify_stake_3u():
    assert classify_stake(0.12, "alta") == 3


def test_classify_stake_2u():
    assert classify_stake(0.08, "media") == 2
    assert classify_stake(0.08, "alta") == 2


def test_classify_stake_1u():
    assert classify_stake(0.06, "baja") == 1


def test_classify_stake_skip():
    assert classify_stake(0.04, "alta") == 0
    assert classify_stake(0.05, "media") == 0


def test_classify_stake_2u_requires_media():
    assert classify_stake(0.08, "baja") == 1


def test_classify_stake_3u_requires_alta():
    assert classify_stake(0.12, "media") == 2


def test_generate_picks_basic():
    predictions = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "prob_home": 0.55,
            "prob_draw": 0.25,
            "prob_away": 0.20,
            "prob_over25": 0.65,
            "prob_btts": 0.50,
            "confidence": "alta",
            "model_variant": "premium",
        }
    ]
    matches_with_odds = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "odd_home": 2.10,
            "odd_draw": 3.50,
            "odd_away": 4.50,
            "odd_over25": 1.70,
            "odd_under25": 2.15,
        }
    ]
    picks = generate_picks(predictions, matches_with_odds)
    assert len(picks) > 0
    for pick in picks:
        assert pick["edge"] > 0.05
        assert pick["stake"] >= 1
        assert pick["market"] in [
            "1x2_home", "1x2_draw", "1x2_away", "over25", "under25"
        ]


def test_generate_picks_no_edge():
    predictions = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "prob_home": 0.40,
            "prob_draw": 0.30,
            "prob_away": 0.30,
            "prob_over25": 0.50,
            "prob_btts": 0.50,
            "confidence": "baja",
            "model_variant": "base",
        }
    ]
    matches_with_odds = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "odd_home": 2.50,
            "odd_draw": 3.30,
            "odd_away": 3.00,
            "odd_over25": 2.00,
            "odd_under25": 1.85,
        }
    ]
    picks = generate_picks(predictions, matches_with_odds)
    assert len(picks) == 0


def test_generate_picks_skips_missing_odds():
    predictions = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "prob_home": 0.55,
            "prob_draw": 0.25,
            "prob_away": 0.20,
            "prob_over25": 0.65,
            "prob_btts": 0.50,
            "confidence": "alta",
            "model_variant": "premium",
        }
    ]
    matches_with_odds = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "odd_home": None,
            "odd_draw": None,
            "odd_away": None,
            "odd_over25": None,
            "odd_under25": None,
        }
    ]
    picks = generate_picks(predictions, matches_with_odds)
    assert len(picks) == 0
