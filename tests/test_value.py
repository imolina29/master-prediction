from backend.betting.value import calculate_edge, classify_stake, generate_picks, remove_vig


def test_remove_vig_three_way():
    odds = [2.10, 3.50, 4.50]
    fair = remove_vig(odds)
    assert len(fair) == 3
    assert abs(sum(fair) - 1.0) < 1e-9
    raw = [1 / o for o in odds]
    overround = sum(raw)
    for i in range(3):
        assert abs(fair[i] - raw[i] / overround) < 1e-9


def test_remove_vig_two_way():
    odds = [1.85, 1.95]
    fair = remove_vig(odds)
    assert len(fair) == 2
    assert abs(sum(fair) - 1.0) < 1e-9


def test_remove_vig_single_fallback():
    odds = [2.50]
    fair = remove_vig(odds)
    assert len(fair) == 1
    assert abs(fair[0] - 1 / 2.50) < 1e-9


def test_calculate_edge_positive():
    market_odds = [2.10, 3.50, 4.50]
    result = calculate_edge(0.55, 0, market_odds)
    fair_probs = remove_vig(market_odds)
    assert abs(result["implied_prob"] - round(fair_probs[0], 4)) < 1e-4
    assert abs(result["edge"] - round(0.55 - fair_probs[0], 4)) < 1e-4
    assert abs(result["expected_value"] - round((0.55 * market_odds[0]) - 1, 4)) < 1e-4


def test_calculate_edge_negative():
    result = calculate_edge(0.30, 0, [2.10, 3.50, 4.50])
    assert result["edge"] < 0


def test_classify_stake_3u():
    assert classify_stake(0.16, "alta") == 3


def test_classify_stake_2u():
    assert classify_stake(0.12, "media") == 2
    assert classify_stake(0.12, "alta") == 2


def test_classify_stake_1u():
    assert classify_stake(0.09, "baja") == 1


def test_classify_stake_skip():
    assert classify_stake(0.05, "alta") == 0
    assert classify_stake(0.07, "media") == 0


def test_classify_stake_2u_requires_media():
    assert classify_stake(0.12, "baja") == 1


def test_classify_stake_3u_requires_alta():
    assert classify_stake(0.16, "media") == 2


def test_generate_picks_basic():
    predictions = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "prob_home": 0.60,
            "prob_draw": 0.22,
            "prob_away": 0.18,
            "prob_over25": 0.70,
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
        assert pick["edge"] > 0.08
        assert pick["stake"] >= 1
        assert pick["market"] in ["1x2_home", "1x2_draw", "1x2_away", "over25", "under25"]


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


def test_generate_picks_no_contradictory():
    predictions = [
        {
            "match_date": "2026-06-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "prob_home": 0.60,
            "prob_draw": 0.22,
            "prob_away": 0.18,
            "prob_over25": 0.70,
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
    h2h_picks = [p for p in picks if p["market"].startswith("1x2")]
    totals_picks = [p for p in picks if p["market"] in ("over25", "under25")]
    assert len(h2h_picks) <= 1, "Should have at most 1 pick per 1x2 market"
    assert len(totals_picks) <= 1, "Should have at most 1 pick per totals market"
    assert len(picks) <= 2, "Should have at most 2 picks per match"


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
