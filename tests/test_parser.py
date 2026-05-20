import pytest

from backend.etl.parser import MatchRow, parse_matches_csv

SAMPLE_CSV = (  # noqa: E501
    "Division,MatchDate,MatchTime,HomeTeam,AwayTeam,HomeElo,AwayElo,Form3Home,Form5Home,"
    "Form3Away,Form5Away,FTHome,FTAway,FTResult,HTHome,HTAway,HTResult,HomeShots,AwayShots,"
    "HomeTarget,AwayTarget,HomeFouls,AwayFouls,HomeCorners,AwayCorners,HomeYellow,AwayYellow,"
    "HomeRed,AwayRed,OddHome,OddDraw,OddAway,MaxHome,MaxDraw,MaxAway,Over25,Under25,"
    "MaxOver25,MaxUnder25,HandiSize,HandiHome,HandiAway,C_LTH,C_LTA,C_VHD,C_VAD,C_HTB,C_PHB\n"
    "E0,2023-08-11,20:00,Burnley,Man City,1465.12,2056.78,0.0,0.0,0.0,0.0,0.0,3.0,A,0.0,2.0,"
    "A,3,14,1,7,11,7,1,7,3,1,0,0,11.0,7.0,1.22,12.0,7.5,1.25,1.53,2.5,1.57,2.55,1.75,2.0,"
    "1.72,0.18,0.22,0.17,0.21,0.12,0.10\n"
    "SP1,2023-08-11,,Ath Bilbao,Real Madrid,1659.45,1985.32,0.0,0.0,0.0,0.0,0.0,2.0,A,0.0,"
    "1.0,A,,,,,,,,,,,,,3.6,3.5,2.0,,,,,,,,,,,,,,,,"
)


def test_parse_complete_row(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(SAMPLE_CSV)

    rows = parse_matches_csv(csv_file)
    assert len(rows) == 2

    row = rows[0]
    assert isinstance(row, MatchRow)
    assert row.division == "E0"
    assert row.match_date == "2023-08-11"
    assert row.home_team == "Burnley"
    assert row.away_team == "Man City"
    assert row.ft_home_goals == 0
    assert row.ft_away_goals == 3
    assert row.ft_result == "A"
    assert row.home_elo == pytest.approx(1465.12, rel=1e-2)
    assert row.odd_home == pytest.approx(11.0)
    assert row.home_shots == 3


def test_parse_row_with_missing_stats(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(SAMPLE_CSV)

    rows = parse_matches_csv(csv_file)
    row = rows[1]  # SP1 row has empty stats

    assert row.division == "SP1"
    assert row.home_team == "Ath Bilbao"
    assert row.home_shots is None
    assert row.odd_max_home is None
    assert row.ft_away_goals == 2


def test_parse_filters_by_division(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(SAMPLE_CSV)

    rows = parse_matches_csv(csv_file, divisions={"E0"})
    assert len(rows) == 1
    assert rows[0].division == "E0"


def test_parse_empty_file(tmp_path):
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("Division,MatchDate,HomeTeam\n")

    rows = parse_matches_csv(csv_file)
    assert rows == []
