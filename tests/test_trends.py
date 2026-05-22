from dashboard.components.trends import stake_analysis_table


def _make_resolved(stake=2, result="win", profit=0.85, **kwargs):
    base = {
        "match_date": "2025-01-15",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "division": "E0",
        "market": "1x2_home",
        "stake": stake,
        "result": result,
        "profit": profit,
    }
    base.update(kwargs)
    return base


def test_stake_analysis_table():
    resolved = [
        _make_resolved(stake=3, result="win", profit=2.55),
        _make_resolved(stake=3, result="win", profit=2.76),
        _make_resolved(stake=2, result="loss", profit=-2),
        _make_resolved(stake=1, result="win", profit=0.85),
        _make_resolved(stake=1, result="loss", profit=-1),
    ]
    table = stake_analysis_table(resolved)
    assert len(table) == 3
    assert table.iloc[0]["Stake"] == 3
    assert table.iloc[0]["Picks"] == 2
    assert table.iloc[0]["Ganados"] == 2


def test_stake_analysis_empty():
    table = stake_analysis_table([])
    assert table.empty
