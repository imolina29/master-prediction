from unittest.mock import MagicMock, patch

from backend.etl.loader import load_matches, match_row_to_dict
from backend.etl.parser import MatchRow


def _make_match(**overrides) -> MatchRow:
    defaults = {
        "division": "E0",
        "match_date": "2024-01-01",
        "match_time": "15:00",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_elo": 1800.0,
        "away_elo": 1750.0,
        "home_form3": 7.0,
        "home_form5": 11.0,
        "away_form3": 5.0,
        "away_form5": 9.0,
        "ft_home_goals": 2,
        "ft_away_goals": 1,
        "ft_result": "H",
        "ht_home_goals": 1,
        "ht_away_goals": 0,
        "ht_result": "H",
        "home_shots": 15,
        "away_shots": 10,
        "home_shots_target": 7,
        "away_shots_target": 4,
        "home_fouls": 10,
        "away_fouls": 12,
        "home_corners": 6,
        "away_corners": 4,
        "home_yellow": 2,
        "away_yellow": 3,
        "home_red": 0,
        "away_red": 0,
        "odd_home": 2.1,
        "odd_draw": 3.4,
        "odd_away": 3.5,
        "odd_max_home": 2.2,
        "odd_max_draw": 3.5,
        "odd_max_away": 3.6,
        "odd_over25": 1.8,
        "odd_under25": 2.0,
        "odd_max_over25": 1.85,
        "odd_max_under25": 2.05,
        "odd_handi_size": -0.5,
        "odd_handi_home": 1.9,
        "odd_handi_away": 1.9,
    }
    defaults.update(overrides)
    return MatchRow(**defaults)


def test_match_row_to_dict_converts_correctly():
    row = _make_match()
    d = match_row_to_dict(row, normalize=lambda x: x)
    assert d["division"] == "E0"
    assert d["home_team"] == "Arsenal"
    assert d["ft_home_goals"] == 2
    assert "id" not in d


def test_match_row_to_dict_normalizes_teams():
    row = _make_match(home_team="Man United", away_team="Man City")
    mapping = {"Man United": "Manchester United", "Man City": "Manchester City"}

    def normalize(x: str) -> str:
        return mapping.get(x, x)

    d = match_row_to_dict(row, normalize=normalize)
    assert d["home_team"] == "Manchester United"
    assert d["away_team"] == "Manchester City"


def test_load_matches_batches_upserts():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])

    rows = [_make_match(match_date=f"2024-01-{i + 1:02d}") for i in range(5)]

    with patch("backend.etl.loader.get_supabase", return_value=mock_client):
        result = load_matches(rows, normalize=lambda x: x, batch_size=2)

    assert result == 5
    assert mock_table.upsert.call_count == 3  # 2 + 2 + 1
