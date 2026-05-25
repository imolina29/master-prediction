from backend.notifications.telegram import build_free_picks


def test_build_free_picks_filters_1x2_only():
    picks = [
        {
            "market": "1x2_home",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "stake": 3,
            "edge": 0.12,
            "odd": 1.85,
        },
        {
            "market": "over25",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "stake": 2,
            "edge": 0.10,
            "odd": 1.90,
        },
        {
            "market": "1x2_away",
            "home_team": "Liverpool",
            "away_team": "Man City",
            "division": "E0",
            "stake": 2,
            "edge": 0.09,
            "odd": 2.50,
        },
    ]
    result = build_free_picks(picks)
    assert len(result) == 2
    assert all(p["market"].startswith("1x2") for p in result)


def test_build_free_picks_filters_by_division():
    picks = [
        {
            "market": "1x2_home",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "division": "E0",
            "stake": 3,
            "edge": 0.12,
            "odd": 1.85,
        },
        {
            "market": "1x2_home",
            "home_team": "Barcelona",
            "away_team": "Madrid",
            "division": "SP1",
            "stake": 3,
            "edge": 0.15,
            "odd": 1.70,
        },
    ]
    result = build_free_picks(picks)
    assert len(result) == 1
    assert result[0]["division"] == "E0"


def test_build_free_picks_includes_world_cup():
    picks = [
        {
            "market": "1x2_home",
            "home_team": "Brazil",
            "away_team": "Germany",
            "division": "WC",
            "stake": 3,
            "edge": 0.12,
            "odd": 2.10,
        },
    ]
    result = build_free_picks(picks)
    assert len(result) == 1


def test_build_free_picks_max_two():
    picks = [
        {
            "market": "1x2_home",
            "home_team": f"Team{i}",
            "away_team": f"Opp{i}",
            "division": "E0",
            "stake": 3 - (i % 3),
            "edge": 0.10 + i * 0.01,
            "odd": 1.80,
        }
        for i in range(5)
    ]
    result = build_free_picks(picks)
    assert len(result) <= 2


def test_build_free_picks_sorted_by_stake_then_edge():
    picks = [
        {
            "market": "1x2_home",
            "home_team": "A",
            "away_team": "B",
            "division": "E0",
            "stake": 1,
            "edge": 0.20,
            "odd": 1.80,
        },
        {
            "market": "1x2_home",
            "home_team": "C",
            "away_team": "D",
            "division": "E0",
            "stake": 3,
            "edge": 0.08,
            "odd": 1.90,
        },
    ]
    result = build_free_picks(picks)
    assert result[0]["home_team"] == "C"


def test_build_free_picks_empty():
    result = build_free_picks([])
    assert result == []
