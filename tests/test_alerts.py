from datetime import date

from backend.notifications.alerts import (
    build_weekly_summary,
    check_high_confidence_picks,
    check_streaks,
)


def _make_pick(stake=1, alerted=False, **kwargs):
    base = {
        "match_date": "2025-01-15",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "division": "E0",
        "market": "1x2_home",
        "odd": 1.85,
        "edge": 0.08,
        "stake": stake,
        "alerted": alerted,
    }
    base.update(kwargs)
    return base


def _make_resolved(result="win", profit=0.85, resolved_at="2025-01-15T10:00:00", **kwargs):
    base = _make_pick(result=result, profit=profit, resolved_at=resolved_at)
    base.update(kwargs)
    return base


def test_high_confidence_filters_stake_3():
    picks = [_make_pick(stake=3), _make_pick(stake=2), _make_pick(stake=1)]
    result = check_high_confidence_picks(picks)
    assert len(result) == 1
    assert result[0]["stake"] == 3


def test_high_confidence_excludes_alerted():
    picks = [_make_pick(stake=3, alerted=True), _make_pick(stake=3, alerted=False)]
    result = check_high_confidence_picks(picks)
    assert len(result) == 1
    assert result[0]["alerted"] is False


def test_high_confidence_empty():
    assert check_high_confidence_picks([]) == []


def test_streak_win_detected():
    resolved = [
        _make_resolved(result="win", resolved_at=f"2025-01-{15 + i}T10:00:00") for i in range(5)
    ]
    streak = check_streaks(resolved)
    assert streak is not None
    assert streak["type"] == "win"
    assert streak["count"] == 5


def test_streak_loss_detected():
    resolved = [
        _make_resolved(result="loss", profit=-1, resolved_at=f"2025-01-{15 + i}T10:00:00")
        for i in range(3)
    ]
    streak = check_streaks(resolved)
    assert streak is not None
    assert streak["type"] == "loss"
    assert streak["count"] == 3


def test_streak_not_enough():
    resolved = [
        _make_resolved(result="win", resolved_at="2025-01-16T10:00:00"),
        _make_resolved(result="win", resolved_at="2025-01-15T10:00:00"),
    ]
    assert check_streaks(resolved) is None


def test_streak_broken():
    resolved = [
        _make_resolved(result="win", resolved_at="2025-01-20T10:00:00"),
        _make_resolved(result="loss", profit=-1, resolved_at="2025-01-19T10:00:00"),
        _make_resolved(result="win", resolved_at="2025-01-18T10:00:00"),
    ]
    assert check_streaks(resolved) is None


def test_streak_empty():
    assert check_streaks([]) is None


def test_weekly_summary():
    picks = [
        _make_resolved(
            result="win",
            profit=0.85,
            match_date="2025-01-13",
            division="E0",
            market="1x2_home",
            stake=2,
        ),
        _make_resolved(
            result="loss",
            profit=-1,
            match_date="2025-01-14",
            division="SP1",
            market="over25",
            stake=1,
        ),
    ]
    summary = build_weekly_summary(picks, date(2025, 1, 13), date(2025, 1, 19))
    assert summary is not None
    assert summary["total"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert summary["profit"] == -0.15
    assert summary["best_league"] == "E0"


def test_weekly_summary_no_picks():
    picks = [_make_resolved(match_date="2025-01-01")]
    summary = build_weekly_summary(picks, date(2025, 1, 13), date(2025, 1, 19))
    assert summary is None
