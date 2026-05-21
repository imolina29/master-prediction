from backend.betting.tracker import (
    calculate_performance,
    resolve_single_pick,
)


def test_resolve_1x2_home_win():
    pick = {"market": "1x2_home", "selection": "H", "odd": 2.10, "stake": 2}
    match = {"ft_result": "H", "ft_home_goals": 2, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 2 * (2.10 - 1)


def test_resolve_1x2_home_loss():
    pick = {"market": "1x2_home", "selection": "H", "odd": 2.10, "stake": 2}
    match = {"ft_result": "D", "ft_home_goals": 1, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "loss"
    assert result["profit"] == -2


def test_resolve_1x2_draw_win():
    pick = {"market": "1x2_draw", "selection": "D", "odd": 3.50, "stake": 1}
    match = {"ft_result": "D", "ft_home_goals": 0, "ft_away_goals": 0}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 1 * (3.50 - 1)


def test_resolve_1x2_away_win():
    pick = {"market": "1x2_away", "selection": "A", "odd": 4.00, "stake": 1}
    match = {"ft_result": "A", "ft_home_goals": 0, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 1 * (4.00 - 1)


def test_resolve_over25_win():
    pick = {"market": "over25", "selection": "Over", "odd": 1.90, "stake": 3}
    match = {"ft_result": "H", "ft_home_goals": 2, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 3 * (1.90 - 1)


def test_resolve_over25_loss():
    pick = {"market": "over25", "selection": "Over", "odd": 1.90, "stake": 2}
    match = {"ft_result": "D", "ft_home_goals": 1, "ft_away_goals": 0}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "loss"
    assert result["profit"] == -2


def test_resolve_under25_win():
    pick = {"market": "under25", "selection": "Under", "odd": 2.00, "stake": 1}
    match = {"ft_result": "D", "ft_home_goals": 1, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "win"
    assert result["profit"] == 1 * (2.00 - 1)


def test_resolve_under25_loss():
    pick = {"market": "under25", "selection": "Under", "odd": 2.00, "stake": 1}
    match = {"ft_result": "H", "ft_home_goals": 2, "ft_away_goals": 1}
    result = resolve_single_pick(pick, match)
    assert result["result"] == "loss"
    assert result["profit"] == -1


def test_calculate_performance_basic():
    resolved = [
        {"result": "win", "profit": 2.2, "stake": 2, "market": "1x2_home"},
        {"result": "loss", "profit": -1, "stake": 1, "market": "1x2_draw"},
        {"result": "win", "profit": 0.9, "stake": 1, "market": "over25"},
    ]
    perf = calculate_performance(resolved)
    assert perf["total_picks"] == 3
    assert perf["wins"] == 2
    assert perf["losses"] == 1
    assert round(perf["profit"], 2) == 2.10
    assert round(perf["roi"], 2) == round(2.10 / 4 * 100, 2)
    assert round(perf["hit_rate"], 4) == round(2 / 3, 4)


def test_calculate_performance_empty():
    perf = calculate_performance([])
    assert perf["total_picks"] == 0
    assert perf["profit"] == 0
    assert perf["roi"] == 0
    assert perf["hit_rate"] == 0


def test_calculate_performance_by_market():
    resolved = [
        {"result": "win", "profit": 2.2, "stake": 2, "market": "1x2_home"},
        {"result": "loss", "profit": -1, "stake": 1, "market": "over25"},
    ]
    perf = calculate_performance(resolved)
    assert "1x2" in perf["by_market"]
    assert "over_under" in perf["by_market"]
    assert perf["by_market"]["1x2"]["picks"] == 1
    assert perf["by_market"]["over_under"]["picks"] == 1
