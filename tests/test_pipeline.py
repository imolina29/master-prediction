import asyncio
from unittest.mock import AsyncMock, patch

from backend.etl.pipeline import run_pipeline

_CSV_HEADER = (
    "Division,MatchDate,MatchTime,HomeTeam,AwayTeam,HomeElo,AwayElo,"
    "Form3Home,Form5Home,Form3Away,Form5Away,FTHome,FTAway,FTResult,"
    "HTHome,HTAway,HTResult,HomeShots,AwayShots,HomeTarget,AwayTarget,"
    "HomeFouls,AwayFouls,HomeCorners,AwayCorners,HomeYellow,AwayYellow,"
    "HomeRed,AwayRed,OddHome,OddDraw,OddAway,MaxHome,MaxDraw,MaxAway,"
    "Over25,Under25,MaxOver25,MaxUnder25,HandiSize,HandiHome,HandiAway,"
    "C_LTH,C_LTA,C_VHD,C_VAD,C_HTB,C_PHB"
)
_CSV_ROW = "E0,2024-01-01,,Arsenal,Chelsea,,,,,,,2.0,1.0,H,1.0,0.0,H,,,,,,,,,,,,,,,,,,,,,,,,,,,,"


def test_pipeline_orchestrates_full_flow(tmp_path):
    csv_content = _CSV_HEADER + "\n" + _CSV_ROW

    csv_path = tmp_path / "Matches.csv"
    csv_path.write_text(csv_content)

    with (
        patch(
            "backend.etl.pipeline.download_matches_csv",
            new_callable=AsyncMock,
            return_value=csv_path,
        ),
        patch("backend.etl.pipeline.load_matches", return_value=1) as mock_load,
    ):
        result = asyncio.run(run_pipeline(data_dir=tmp_path))

    assert result["downloaded"] is True
    assert result["parsed"] == 1
    assert result["loaded"] == 1
    mock_load.assert_called_once()
