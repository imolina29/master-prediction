from unittest.mock import MagicMock, patch

import pytest

from backend.etl.understat import (
    LEAGUE_MAP,
    fetch_league_season,
    parse_matches,
)

SAMPLE_API_RESPONSE = {
    "dates": [
        {
            "id": "1001",
            "isResult": True,
            "h": {"id": "1", "title": "Arsenal", "short_title": "ARS"},
            "a": {"id": "2", "title": "Manchester City", "short_title": "MCI"},
            "goals": {"h": "2", "a": "1"},
            "xG": {"h": "1.85", "a": "1.23"},
            "datetime": "2024-08-17 15:00:00",
            "forecast": {"w": "0.5", "d": "0.3", "l": "0.2"},
        },
        {
            "id": "1002",
            "isResult": True,
            "h": {"id": "3", "title": "Wolverhampton Wanderers", "short_title": "WOL"},
            "a": {"id": "4", "title": "Chelsea", "short_title": "CHE"},
            "goals": {"h": "0", "a": "3"},
            "xG": {"h": "0.45", "a": "2.10"},
            "datetime": "2024-08-17 17:30:00",
            "forecast": {"w": "0.2", "d": "0.3", "l": "0.5"},
        },
    ],
    "teams": {},
    "players": [],
}


def test_league_map_has_all_five():
    assert set(LEAGUE_MAP.keys()) == {"EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"}
    assert LEAGUE_MAP["EPL"] == "E0"
    assert LEAGUE_MAP["La_Liga"] == "SP1"


def test_parse_matches_extracts_fields():
    rows = parse_matches(SAMPLE_API_RESPONSE["dates"], division="E0")
    assert len(rows) == 2

    row = rows[0]
    assert row["division"] == "E0"
    assert row["match_date"] == "2024-08-17"
    assert row["home_team"] == "Arsenal"
    assert row["away_team"] == "Manchester City"
    assert row["home_xg"] == pytest.approx(1.85)
    assert row["away_xg"] == pytest.approx(1.23)
    assert row["home_goals"] == 2
    assert row["away_goals"] == 1
    assert row["source"] == "understat"


def test_parse_matches_raw_team_names():
    rows = parse_matches(SAMPLE_API_RESPONSE["dates"], division="E0")
    assert rows[1]["home_team"] == "Wolverhampton Wanderers"


def test_parse_matches_skips_unplayed():
    dates = [
        {
            "id": "9999",
            "isResult": False,
            "h": {"id": "1", "title": "A", "short_title": "A"},
            "a": {"id": "2", "title": "B", "short_title": "B"},
            "goals": {"h": "0", "a": "0"},
            "xG": {"h": "0", "a": "0"},
            "datetime": "2025-05-30 15:00:00",
            "forecast": {"w": "0.5", "d": "0.3", "l": "0.2"},
        }
    ]
    rows = parse_matches(dates, division="E0")
    assert len(rows) == 0


def test_fetch_league_season():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_API_RESPONSE

    with patch(
        "backend.etl.understat.get_with_retry", return_value=mock_response
    ) as mock_get:
        result = fetch_league_season("EPL", 2024)

    assert result == SAMPLE_API_RESPONSE
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    assert "getLeagueData/EPL/2024" in call_args[0][0]
