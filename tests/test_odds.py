from backend.etl.odds import SPORT_KEY_MAP, parse_odds, run_odds_sync  # noqa: F401
from backend.services.teams import TeamNormalizer

SAMPLE_API_RESPONSE = [
    {
        "id": "abc123",
        "sport_key": "soccer_epl",
        "commence_time": "2026-05-25T15:00:00Z",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "bookmakers": [
            {
                "key": "pinnacle",
                "title": "Pinnacle",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.10},
                            {"name": "Chelsea", "price": 3.50},
                            {"name": "Draw", "price": 3.20},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": 2.5, "price": 1.90},
                            {"name": "Under", "point": 2.5, "price": 1.95},
                        ],
                    },
                ],
            },
            {
                "key": "bet365",
                "title": "Bet365",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.05},
                            {"name": "Chelsea", "price": 3.40},
                            {"name": "Draw", "price": 3.30},
                        ],
                    },
                ],
            },
        ],
    }
]


def test_sport_key_map_covers_all_divisions():
    expected = {"E0", "SP1", "D1", "I1", "F1", "EC", "WC"}
    assert set(SPORT_KEY_MAP.values()) == expected


def test_parse_odds_extracts_best_odds():
    normalizer = TeamNormalizer()
    records = parse_odds(SAMPLE_API_RESPONSE, "E0", normalizer)

    assert len(records) == 1
    r = records[0]
    assert r["home_team"] == "Arsenal"
    assert r["away_team"] == "Chelsea"
    assert r["division"] == "E0"
    assert r["match_date"] == "2026-05-25"
    assert r["odd_home"] == 2.10
    assert r["odd_away"] == 3.50
    assert r["odd_draw"] == 3.20
    assert r["odd_over25"] == 1.90
    assert r["odd_under25"] == 1.95
    assert r["bookmaker_h2h"] == "pinnacle"


def test_parse_odds_missing_totals():
    events = [
        {
            "id": "xyz",
            "sport_key": "soccer_epl",
            "commence_time": "2026-05-25T15:00:00Z",
            "home_team": "Liverpool",
            "away_team": "Everton",
            "bookmakers": [
                {
                    "key": "bet365",
                    "title": "Bet365",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Liverpool", "price": 1.50},
                                {"name": "Everton", "price": 6.00},
                                {"name": "Draw", "price": 4.20},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    normalizer = TeamNormalizer()
    records = parse_odds(events, "E0", normalizer)
    assert len(records) == 1
    assert records[0]["odd_over25"] is None
    assert records[0]["odd_under25"] is None


def test_parse_odds_empty_bookmakers():
    events = [
        {
            "id": "xyz",
            "sport_key": "soccer_epl",
            "commence_time": "2026-05-25T15:00:00Z",
            "home_team": "Liverpool",
            "away_team": "Everton",
            "bookmakers": [],
        }
    ]
    normalizer = TeamNormalizer()
    records = parse_odds(events, "E0", normalizer)
    assert len(records) == 0
