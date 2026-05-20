# Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data foundation — ingest 50K+ football matches from xgabora's dataset into Supabase, normalize team names, automate daily updates via GitHub Actions, and establish CI with ruff + pytest.

**Architecture:** Monolith backend in Python. Raw CSV downloaded from GitHub → parsed with pandas → normalized → stored in Supabase PostgreSQL. A canonical_teams table maps variant team names to stable UUIDs. DuckDB/Parquet used as local analytical layer. GitHub Actions handles CI and scheduled ETL.

**Tech Stack:** Python 3.12, Supabase (PostgreSQL free tier), pandas, DuckDB, httpx, pytest, ruff, GitHub Actions

---

## File Structure

```
backend/
├── config.py                  # Pydantic settings (env vars, Supabase config)
├── db/
│   ├── __init__.py
│   ├── client.py              # Supabase client singleton
│   ├── schema.sql             # DDL for all tables
│   └── migrations/            # Future Alembic migrations (not Phase 1)
├── etl/
│   ├── __init__.py
│   ├── downloader.py          # Download CSV from GitHub
│   ├── parser.py              # Parse + validate CSV into typed dicts
│   ├── loader.py              # Upsert parsed data into Supabase
│   └── pipeline.py            # Orchestrator: download → parse → normalize → load
├── services/
│   ├── __init__.py
│   └── teams.py               # Team normalization logic
├── utils/
│   ├── __init__.py
│   └── logging.py             # Structured logging setup
tests/
├── conftest.py                # Shared fixtures
├── test_config.py             # Config loading tests
├── test_downloader.py         # Download tests
├── test_parser.py             # CSV parsing tests
├── test_teams.py              # Team normalization tests
├── test_loader.py             # DB loading tests
├── test_pipeline.py           # Integration tests
data/
├── team_mappings.json         # Canonical team name mappings
.github/
├── workflows/
│   ├── ci.yml                 # Lint + test on push/PR
│   └── etl.yml                # Scheduled ETL pipeline
pyproject.toml                 # ruff config, pytest config, project metadata
```

---

## Task 1: Project Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `backend/config.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create pyproject.toml with ruff + pytest config**

```toml
[project]
name = "master-prediction"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = [
    "integration: marks tests that need a real database connection",
]
```

- [ ] **Step 2: Write the failing test for config**

```python
# tests/test_config.py
import os

def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    from backend.config import Settings
    settings = Settings()

    assert settings.supabase_url == "https://test.supabase.co"
    assert settings.supabase_key == "test-key"
    assert settings.supabase_service_key == "test-service-key"
    assert settings.database_url == "postgresql://localhost/test"
    assert settings.env == "development"
    assert settings.log_level == "INFO"


def test_config_defaults():
    from backend.config import Settings
    settings = Settings(
        supabase_url="https://x.supabase.co",
        supabase_key="k",
        supabase_service_key="sk",
        database_url="postgresql://localhost/test",
    )
    assert settings.env == "development"
    assert settings.log_level == "INFO"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `cannot import name 'Settings' from 'backend.config'`

- [ ] **Step 4: Implement config**

```python
# backend/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    database_url: str
    env: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

- [ ] **Step 5: Create conftest with shared fixtures**

```python
# tests/conftest.py
import pytest
from backend.config import Settings


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/test")
    return Settings()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml backend/config.py tests/conftest.py tests/test_config.py
git commit -m "feat: add project config with pydantic-settings"
```

---

## Task 2: Supabase DB Client + Schema

**Files:**
- Create: `backend/db/client.py`
- Create: `backend/db/schema.sql`

- [ ] **Step 1: Write schema.sql**

This defines 3 tables: `competitions`, `teams`, `matches`. The `teams` table is the canonical source for team identity. `matches` references teams by `canonical_name` (denormalized for query simplicity — no joins needed for most reads).

```sql
-- backend/db/schema.sql

-- Competitions (leagues + tournaments)
CREATE TABLE IF NOT EXISTS competitions (
    code TEXT PRIMARY KEY,           -- e.g. 'E0', 'SP1', 'EC'
    name TEXT NOT NULL,              -- e.g. 'Premier League'
    country TEXT NOT NULL            -- e.g. 'England'
);

INSERT INTO competitions (code, name, country) VALUES
    ('E0', 'Premier League', 'England'),
    ('E1', 'Championship', 'England'),
    ('SP1', 'La Liga', 'Spain'),
    ('SP2', 'La Liga 2', 'Spain'),
    ('I1', 'Serie A', 'Italy'),
    ('I2', 'Serie B', 'Italy'),
    ('D1', 'Bundesliga', 'Germany'),
    ('D2', '2. Bundesliga', 'Germany'),
    ('F1', 'Ligue 1', 'France'),
    ('F2', 'Ligue 2', 'France'),
    ('EC', 'Champions League', 'Europe')
ON CONFLICT (code) DO NOTHING;

-- Canonical teams
CREATE TABLE IF NOT EXISTS teams (
    canonical_name TEXT PRIMARY KEY, -- e.g. 'Manchester United'
    short_name TEXT,                 -- e.g. 'Man Utd'
    country TEXT                     -- e.g. 'England'
);

-- Team name aliases (variant → canonical)
CREATE TABLE IF NOT EXISTS team_aliases (
    alias TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL REFERENCES teams(canonical_name)
);

-- Match results + odds
CREATE TABLE IF NOT EXISTS matches (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    division TEXT NOT NULL REFERENCES competitions(code),
    match_date DATE NOT NULL,
    match_time TEXT,
    home_team TEXT NOT NULL,          -- canonical name
    away_team TEXT NOT NULL,          -- canonical name
    -- Elo
    home_elo REAL,
    away_elo REAL,
    -- Form
    home_form3 REAL,
    home_form5 REAL,
    away_form3 REAL,
    away_form5 REAL,
    -- Full time
    ft_home_goals SMALLINT,
    ft_away_goals SMALLINT,
    ft_result CHAR(1),               -- H, D, A
    -- Half time
    ht_home_goals SMALLINT,
    ht_away_goals SMALLINT,
    ht_result CHAR(1),
    -- Stats
    home_shots SMALLINT,
    away_shots SMALLINT,
    home_shots_target SMALLINT,
    away_shots_target SMALLINT,
    home_fouls SMALLINT,
    away_fouls SMALLINT,
    home_corners SMALLINT,
    away_corners SMALLINT,
    home_yellow SMALLINT,
    away_yellow SMALLINT,
    home_red SMALLINT,
    away_red SMALLINT,
    -- Odds
    odd_home REAL,
    odd_draw REAL,
    odd_away REAL,
    odd_max_home REAL,
    odd_max_draw REAL,
    odd_max_away REAL,
    odd_over25 REAL,
    odd_under25 REAL,
    odd_max_over25 REAL,
    odd_max_under25 REAL,
    odd_handi_size REAL,
    odd_handi_home REAL,
    odd_handi_away REAL,
    -- Dedup
    UNIQUE(division, match_date, home_team, away_team)
);

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_division ON matches(division);
CREATE INDEX IF NOT EXISTS idx_matches_home ON matches(home_team);
CREATE INDEX IF NOT EXISTS idx_matches_away ON matches(away_team);
```

- [ ] **Step 2: Write the DB client**

```python
# backend/db/client.py
from supabase import create_client, Client
from backend.config import Settings


_client: Client | None = None


def get_supabase(settings: Settings | None = None) -> Client:
    global _client
    if _client is None:
        if settings is None:
            settings = Settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def reset_client():
    global _client
    _client = None
```

- [ ] **Step 3: Commit**

```bash
git add backend/db/client.py backend/db/schema.sql
git commit -m "feat: add Supabase schema and client"
```

---

## Task 3: CSV Downloader

**Files:**
- Create: `backend/etl/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_downloader.py
from pathlib import Path
from unittest.mock import AsyncMock, patch


def test_download_creates_file(tmp_path):
    csv_content = b"Division,MatchDate,HomeTeam\nE0,2024-01-01,Arsenal\n"

    with patch("backend.etl.downloader.httpx.AsyncClient") as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = csv_content
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        import asyncio
        from backend.etl.downloader import download_matches_csv

        output = asyncio.run(download_matches_csv(tmp_path))

        assert output.exists()
        assert output.read_bytes() == csv_content


def test_download_raises_on_failure(tmp_path):
    with patch("backend.etl.downloader.httpx.AsyncClient") as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = AsyncMock(
            side_effect=Exception("404 Not Found")
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        import asyncio
        import pytest
        from backend.etl.downloader import download_matches_csv

        with pytest.raises(Exception):
            asyncio.run(download_matches_csv(tmp_path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_downloader.py -v`
Expected: FAIL — `cannot import name 'download_matches_csv'`

- [ ] **Step 3: Implement downloader**

```python
# backend/etl/downloader.py
import logging
from pathlib import Path

import httpx

MATCHES_URL = (
    "https://raw.githubusercontent.com/xgabora/"
    "Club-Football-Match-Data-2000-2025/main/data/Matches.csv"
)

logger = logging.getLogger(__name__)


async def download_matches_csv(dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    output_path = dest_dir / "Matches.csv"

    async with httpx.AsyncClient(timeout=120.0) as client:
        logger.info("Downloading matches CSV from %s", MATCHES_URL)
        response = await client.get(MATCHES_URL)
        response.raise_for_status()

    output_path.write_bytes(response.content)
    size_mb = len(response.content) / (1024 * 1024)
    logger.info("Downloaded %.1f MB to %s", size_mb, output_path)
    return output_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_downloader.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/etl/downloader.py tests/test_downloader.py
git commit -m "feat: add CSV downloader for xgabora match data"
```

---

## Task 4: CSV Parser

**Files:**
- Create: `backend/etl/parser.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_parser.py
from pathlib import Path
from backend.etl.parser import parse_matches_csv, MatchRow

SAMPLE_CSV = """Division,MatchDate,MatchTime,HomeTeam,AwayTeam,HomeElo,AwayElo,Form3Home,Form5Home,Form3Away,Form5Away,FTHome,FTAway,FTResult,HTHome,HTAway,HTResult,HomeShots,AwayShots,HomeTarget,AwayTarget,HomeFouls,AwayFouls,HomeCorners,AwayCorners,HomeYellow,AwayYellow,HomeRed,AwayRed,OddHome,OddDraw,OddAway,MaxHome,MaxDraw,MaxAway,Over25,Under25,MaxOver25,MaxUnder25,HandiSize,HandiHome,HandiAway,C_LTH,C_LTA,C_VHD,C_VAD,C_HTB,C_PHB
E0,2023-08-11,20:00,Burnley,Man City,1465.12,2056.78,0.0,0.0,0.0,0.0,0.0,3.0,A,0.0,2.0,A,3,14,1,7,11,7,1,7,3,1,0,0,11.0,7.0,1.22,12.0,7.5,1.25,1.53,2.5,1.57,2.55,1.75,2.0,1.72,0.18,0.22,0.17,0.21,0.12,0.10
SP1,2023-08-11,,Ath Bilbao,Real Madrid,1659.45,1985.32,0.0,0.0,0.0,0.0,0.0,2.0,A,0.0,1.0,A,,,,,,,,,,,,,,3.6,3.5,2.0,,,,,,,,,,,,"""


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


import pytest
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_parser.py -v`
Expected: FAIL — `cannot import name 'parse_matches_csv'`

- [ ] **Step 3: Implement parser**

```python
# backend/etl/parser.py
import csv
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

TARGET_DIVISIONS = {"E0", "E1", "SP1", "SP2", "I1", "I2", "D1", "D2", "F1", "F2", "EC"}

CSV_TO_FIELD = {
    "Division": "division",
    "MatchDate": "match_date",
    "MatchTime": "match_time",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "HomeElo": "home_elo",
    "AwayElo": "away_elo",
    "Form3Home": "home_form3",
    "Form5Home": "home_form5",
    "Form3Away": "away_form3",
    "Form5Away": "away_form5",
    "FTHome": "ft_home_goals",
    "FTAway": "ft_away_goals",
    "FTResult": "ft_result",
    "HTHome": "ht_home_goals",
    "HTAway": "ht_away_goals",
    "HTResult": "ht_result",
    "HomeShots": "home_shots",
    "AwayShots": "away_shots",
    "HomeTarget": "home_shots_target",
    "AwayTarget": "away_shots_target",
    "HomeFouls": "home_fouls",
    "AwayFouls": "away_fouls",
    "HomeCorners": "home_corners",
    "AwayCorners": "away_corners",
    "HomeYellow": "home_yellow",
    "AwayYellow": "away_yellow",
    "HomeRed": "home_red",
    "AwayRed": "away_red",
    "OddHome": "odd_home",
    "OddDraw": "odd_draw",
    "OddAway": "odd_away",
    "MaxHome": "odd_max_home",
    "MaxDraw": "odd_max_draw",
    "MaxAway": "odd_max_away",
    "Over25": "odd_over25",
    "Under25": "odd_under25",
    "MaxOver25": "odd_max_over25",
    "MaxUnder25": "odd_max_under25",
    "HandiSize": "odd_handi_size",
    "HandiHome": "odd_handi_home",
    "HandiAway": "odd_handi_away",
}

TEXT_FIELDS = {"division", "match_date", "match_time", "home_team", "away_team", "ft_result", "ht_result"}
INT_FIELDS = {
    "ft_home_goals", "ft_away_goals", "ht_home_goals", "ht_away_goals",
    "home_shots", "away_shots", "home_shots_target", "away_shots_target",
    "home_fouls", "away_fouls", "home_corners", "away_corners",
    "home_yellow", "away_yellow", "home_red", "away_red",
}


@dataclass
class MatchRow:
    division: str
    match_date: str
    match_time: str | None
    home_team: str
    away_team: str
    home_elo: float | None
    away_elo: float | None
    home_form3: float | None
    home_form5: float | None
    away_form3: float | None
    away_form5: float | None
    ft_home_goals: int | None
    ft_away_goals: int | None
    ft_result: str | None
    ht_home_goals: int | None
    ht_away_goals: int | None
    ht_result: str | None
    home_shots: int | None
    away_shots: int | None
    home_shots_target: int | None
    away_shots_target: int | None
    home_fouls: int | None
    away_fouls: int | None
    home_corners: int | None
    away_corners: int | None
    home_yellow: int | None
    away_yellow: int | None
    home_red: int | None
    away_red: int | None
    odd_home: float | None
    odd_draw: float | None
    odd_away: float | None
    odd_max_home: float | None
    odd_max_draw: float | None
    odd_max_away: float | None
    odd_over25: float | None
    odd_under25: float | None
    odd_max_over25: float | None
    odd_max_under25: float | None
    odd_handi_size: float | None
    odd_handi_home: float | None
    odd_handi_away: float | None


def _parse_value(raw: str, field: str) -> str | int | float | None:
    stripped = raw.strip()
    if not stripped:
        return None
    if field in TEXT_FIELDS:
        return stripped
    if field in INT_FIELDS:
        return int(float(stripped))
    return float(stripped)


def parse_matches_csv(
    path: Path,
    divisions: set[str] | None = None,
) -> list[MatchRow]:
    if divisions is None:
        divisions = TARGET_DIVISIONS

    rows: list[MatchRow] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            div = raw_row.get("Division", "").strip()
            if div not in divisions:
                continue

            parsed = {}
            for csv_col, field_name in CSV_TO_FIELD.items():
                raw_val = raw_row.get(csv_col, "")
                parsed[field_name] = _parse_value(raw_val, field_name)

            if not parsed.get("match_date") or not parsed.get("home_team"):
                continue

            rows.append(MatchRow(**parsed))

    logger.info("Parsed %d matches from %s (filtered to %s)", len(rows), path.name, divisions)
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_parser.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/etl/parser.py tests/test_parser.py
git commit -m "feat: add CSV parser with typed MatchRow dataclass"
```

---

## Task 5: Team Normalization Service

**Files:**
- Create: `data/team_mappings.json`
- Create: `backend/services/teams.py`
- Create: `tests/test_teams.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_teams.py
from backend.services.teams import TeamNormalizer


def test_normalize_known_alias():
    tn = TeamNormalizer()
    assert tn.normalize("Man United") == "Manchester United"
    assert tn.normalize("Man City") == "Manchester City"
    assert tn.normalize("Ath Madrid") == "Atletico Madrid"
    assert tn.normalize("Ath Bilbao") == "Athletic Bilbao"


def test_normalize_already_canonical():
    tn = TeamNormalizer()
    assert tn.normalize("Arsenal") == "Arsenal"
    assert tn.normalize("Barcelona") == "Barcelona"


def test_normalize_duplicate_variants():
    tn = TeamNormalizer()
    assert tn.normalize("MGladbach") == tn.normalize("M'gladbach")
    assert tn.normalize("Nott'm Forest") == tn.normalize("Nottm Forest")


def test_normalize_unknown_passes_through():
    tn = TeamNormalizer()
    assert tn.normalize("Some Unknown FC") == "Some Unknown FC"


def test_get_all_aliases():
    tn = TeamNormalizer()
    aliases = tn.get_aliases("Manchester United")
    assert "Man United" in aliases


def test_all_teams_list():
    tn = TeamNormalizer()
    teams = tn.all_canonical()
    assert "Manchester United" in teams
    assert "Barcelona" in teams
    assert len(teams) > 50
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_teams.py -v`
Expected: FAIL — `cannot import name 'TeamNormalizer'`

- [ ] **Step 3: Create team_mappings.json**

This maps every variant name in the xgabora dataset to a canonical name. Only entries where the canonical differs from the source name need to be listed. Teams that appear with their canonical name already (e.g., "Arsenal") don't need an entry.

```json
{
    "_comment": "Maps source team name variants to canonical names. Only non-obvious mappings needed.",
    "aliases": {
        "Man United": "Manchester United",
        "Man City": "Manchester City",
        "Ath Madrid": "Atletico Madrid",
        "Ath Bilbao": "Athletic Bilbao",
        "Betis": "Real Betis",
        "Sociedad": "Real Sociedad",
        "Sp Gijon": "Sporting Gijon",
        "Wolves": "Wolverhampton",
        "MGladbach": "Borussia Monchengladbach",
        "M'gladbach": "Borussia Monchengladbach",
        "Nott'm Forest": "Nottingham Forest",
        "Nottm Forest": "Nottingham Forest",
        "Sheffield United": "Sheffield United",
        "QPR": "Queens Park Rangers",
        "Hertha": "Hertha Berlin",
        "Inter": "Inter Milan",
        "Milan": "AC Milan",
        "Celta": "Celta Vigo",
        "Alaves": "Deportivo Alaves",
        "Malaga": "Malaga CF",
        "Espanol": "Espanyol",
        "La Coruna": "Deportivo La Coruna",
        "Vallecano": "Rayo Vallecano",
        "Cadiz": "Cadiz CF",
        "Elche": "Elche CF",
        "Stoke": "Stoke City",
        "Hull": "Hull City",
        "Derby": "Derby County",
        "Leeds": "Leeds United",
        "Bolton": "Bolton Wanderers",
        "Wigan": "Wigan Athletic",
        "Luton": "Luton Town",
        "Mainz": "Mainz 05",
        "Nimes": "Nimes Olympique"
    },
    "canonical_metadata": {
        "Manchester United": {"country": "England", "short": "Man Utd"},
        "Manchester City": {"country": "England", "short": "Man City"},
        "Arsenal": {"country": "England", "short": "Arsenal"},
        "Liverpool": {"country": "England", "short": "Liverpool"},
        "Chelsea": {"country": "England", "short": "Chelsea"},
        "Tottenham": {"country": "England", "short": "Spurs"},
        "Barcelona": {"country": "Spain", "short": "Barca"},
        "Real Madrid": {"country": "Spain", "short": "R. Madrid"},
        "Atletico Madrid": {"country": "Spain", "short": "Atl. Madrid"},
        "Bayern Munich": {"country": "Germany", "short": "Bayern"},
        "Borussia Dortmund": {"country": "Germany", "short": "Dortmund"},
        "Borussia Monchengladbach": {"country": "Germany", "short": "Gladbach"},
        "Juventus": {"country": "Italy", "short": "Juve"},
        "AC Milan": {"country": "Italy", "short": "Milan"},
        "Inter Milan": {"country": "Italy", "short": "Inter"},
        "Napoli": {"country": "Italy", "short": "Napoli"},
        "Paris SG": {"country": "France", "short": "PSG"},
        "Lyon": {"country": "France", "short": "Lyon"},
        "Marseille": {"country": "France", "short": "OM"},
        "Nottingham Forest": {"country": "England", "short": "Forest"},
        "Wolverhampton": {"country": "England", "short": "Wolves"},
        "Queens Park Rangers": {"country": "England", "short": "QPR"}
    }
}
```

- [ ] **Step 4: Implement TeamNormalizer**

```python
# backend/services/teams.py
import json
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

MAPPINGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "team_mappings.json"


class TeamNormalizer:
    def __init__(self, mappings_path: Path = MAPPINGS_PATH):
        data = json.loads(mappings_path.read_text(encoding="utf-8"))
        self._alias_to_canonical: dict[str, str] = data.get("aliases", {})
        self._metadata: dict[str, dict] = data.get("canonical_metadata", {})

        self._canonical_to_aliases: dict[str, list[str]] = defaultdict(list)
        for alias, canonical in self._alias_to_canonical.items():
            self._canonical_to_aliases[canonical].append(alias)

    def normalize(self, name: str) -> str:
        return self._alias_to_canonical.get(name, name)

    def get_aliases(self, canonical_name: str) -> list[str]:
        return self._canonical_to_aliases.get(canonical_name, [])

    def get_metadata(self, canonical_name: str) -> dict | None:
        return self._metadata.get(canonical_name)

    def all_canonical(self) -> set[str]:
        canonical = set(self._alias_to_canonical.values())
        canonical.update(self._metadata.keys())
        return canonical
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_teams.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add data/team_mappings.json backend/services/teams.py tests/test_teams.py
git commit -m "feat: add team name normalization with canonical mappings"
```

---

## Task 6: Database Loader

**Files:**
- Create: `backend/etl/loader.py`
- Create: `tests/test_loader.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_loader.py
from dataclasses import asdict
from unittest.mock import MagicMock, call, patch

from backend.etl.parser import MatchRow
from backend.etl.loader import load_matches, match_row_to_dict


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
    normalize = lambda x: {"Man United": "Manchester United", "Man City": "Manchester City"}.get(x, x)
    d = match_row_to_dict(row, normalize=normalize)
    assert d["home_team"] == "Manchester United"
    assert d["away_team"] == "Manchester City"


def test_load_matches_batches_upserts():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])

    rows = [_make_match(match_date=f"2024-01-{i+1:02d}") for i in range(5)]

    with patch("backend.etl.loader.get_supabase", return_value=mock_client):
        result = load_matches(rows, normalize=lambda x: x, batch_size=2)

    assert result == 5
    assert mock_table.upsert.call_count == 3  # 2 + 2 + 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_loader.py -v`
Expected: FAIL — `cannot import name 'load_matches'`

- [ ] **Step 3: Implement loader**

```python
# backend/etl/loader.py
import logging
from dataclasses import asdict
from typing import Callable

from backend.db.client import get_supabase
from backend.etl.parser import MatchRow

logger = logging.getLogger(__name__)


def match_row_to_dict(row: MatchRow, normalize: Callable[[str], str]) -> dict:
    d = asdict(row)
    d["home_team"] = normalize(d["home_team"])
    d["away_team"] = normalize(d["away_team"])
    return d


def load_matches(
    rows: list[MatchRow],
    normalize: Callable[[str], str],
    batch_size: int = 500,
) -> int:
    client = get_supabase()
    total = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        records = [match_row_to_dict(r, normalize) for r in batch]

        client.table("matches").upsert(
            records,
            on_conflict="division,match_date,home_team,away_team",
        ).execute()

        total += len(batch)
        logger.info("Loaded batch %d-%d (%d total)", i, i + len(batch), total)

    return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_loader.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/etl/loader.py tests/test_loader.py
git commit -m "feat: add batch loader for upserting matches to Supabase"
```

---

## Task 7: ETL Pipeline Orchestrator

**Files:**
- Create: `backend/etl/pipeline.py`
- Create: `tests/test_pipeline.py`
- Create: `scripts/run_etl.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline.py
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from backend.etl.pipeline import run_pipeline


def test_pipeline_orchestrates_full_flow(tmp_path):
    csv_content = "Division,MatchDate,MatchTime,HomeTeam,AwayTeam,HomeElo,AwayElo,Form3Home,Form5Home,Form3Away,Form5Away,FTHome,FTAway,FTResult,HTHome,HTAway,HTResult,HomeShots,AwayShots,HomeTarget,AwayTarget,HomeFouls,AwayFouls,HomeCorners,AwayCorners,HomeYellow,AwayYellow,HomeRed,AwayRed,OddHome,OddDraw,OddAway,MaxHome,MaxDraw,MaxAway,Over25,Under25,MaxOver25,MaxUnder25,HandiSize,HandiHome,HandiAway,C_LTH,C_LTA,C_VHD,C_VAD,C_HTB,C_PHB\nE0,2024-01-01,,Arsenal,Chelsea,,,,,,,2.0,1.0,H,1.0,0.0,H,,,,,,,,,,,,,,,,,,,,,,,,,,,,,"

    csv_path = tmp_path / "Matches.csv"
    csv_path.write_text(csv_content)

    with (
        patch("backend.etl.pipeline.download_matches_csv", new_callable=AsyncMock, return_value=csv_path),
        patch("backend.etl.pipeline.load_matches", return_value=1) as mock_load,
    ):
        result = asyncio.run(run_pipeline(data_dir=tmp_path))

    assert result["downloaded"] is True
    assert result["parsed"] == 1
    assert result["loaded"] == 1
    mock_load.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `cannot import name 'run_pipeline'`

- [ ] **Step 3: Implement pipeline**

```python
# backend/etl/pipeline.py
import asyncio
import logging
from pathlib import Path

from backend.etl.downloader import download_matches_csv
from backend.etl.loader import load_matches
from backend.etl.parser import parse_matches_csv
from backend.services.teams import TeamNormalizer

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


async def run_pipeline(
    data_dir: Path = DEFAULT_DATA_DIR,
    divisions: set[str] | None = None,
) -> dict:
    logger.info("Starting ETL pipeline")

    csv_path = await download_matches_csv(data_dir)
    logger.info("Download complete: %s", csv_path)

    rows = parse_matches_csv(csv_path, divisions=divisions)
    logger.info("Parsed %d matches", len(rows))

    normalizer = TeamNormalizer()
    loaded = load_matches(rows, normalize=normalizer.normalize)
    logger.info("Loaded %d matches to database", loaded)

    return {"downloaded": True, "parsed": len(rows), "loaded": loaded}
```

- [ ] **Step 4: Create runner script**

```python
# scripts/run_etl.py
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    from backend.etl.pipeline import run_pipeline
    result = asyncio.run(run_pipeline())
    logging.info("Pipeline result: %s", result)
    if result["loaded"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add backend/etl/pipeline.py tests/test_pipeline.py scripts/run_etl.py
git commit -m "feat: add ETL pipeline orchestrator and runner script"
```

---

## Task 8: CI Workflow (GitHub Actions)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Lint with ruff
        run: ruff check .

      - name: Format check with ruff
        run: ruff format --check .

      - name: Run tests
        run: python -m pytest tests/ -v --ignore=tests/test_pipeline_integration.py
        env:
          SUPABASE_URL: https://fake.supabase.co
          SUPABASE_KEY: fake-key
          SUPABASE_SERVICE_KEY: fake-service-key
          DATABASE_URL: postgresql://localhost/fake
```

- [ ] **Step 2: Verify lint passes locally**

Run: `ruff check . && ruff format --check .`
Expected: All checks passed (fix any issues before committing)

- [ ] **Step 3: Verify all tests pass locally**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint and test workflow with ruff + pytest"
```

---

## Task 9: ETL Cron Workflow (GitHub Actions)

**Files:**
- Create: `.github/workflows/etl.yml`

- [ ] **Step 1: Create ETL workflow**

```yaml
# .github/workflows/etl.yml
name: ETL Pipeline

on:
  schedule:
    - cron: "0 6 * * *"  # Daily at 6 AM UTC
  workflow_dispatch:       # Manual trigger

jobs:
  run-etl:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run ETL pipeline
        run: python scripts/run_etl.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/etl.yml
git commit -m "ci: add daily ETL cron workflow"
```

---

## Task 10: Supabase Setup + First Real Load

This is a manual + integration task — no unit tests, but we verify the real connection works.

- [ ] **Step 1: Create Supabase project**

Go to https://supabase.com and create a free project called `master-prediction`. Save the credentials:
- Project URL → `SUPABASE_URL`
- Anon key → `SUPABASE_KEY`
- Service role key → `SUPABASE_SERVICE_KEY`
- Connection string → `DATABASE_URL`

- [ ] **Step 2: Create .env from template**

```bash
cp .env.example .env
# Edit .env with real Supabase credentials
```

- [ ] **Step 3: Run schema.sql in Supabase SQL Editor**

Go to Supabase Dashboard → SQL Editor → paste contents of `backend/db/schema.sql` → Run.

Verify tables were created: `competitions`, `teams`, `team_aliases`, `matches`.

- [ ] **Step 4: Run the ETL pipeline for real**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/run_etl.py
```

Expected: ~50K matches loaded (Top 5 leagues + CL + second divisions).

- [ ] **Step 5: Verify in Supabase Dashboard**

Go to Table Editor → `matches` table. Verify:
- Data is there
- Team names are normalized (e.g., "Manchester United" not "Man United")
- Odds are populated
- Multiple divisions present

- [ ] **Step 6: Add GitHub Secrets for ETL workflow**

Go to repo Settings → Secrets → Actions → add:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_KEY`
- `DATABASE_URL`

- [ ] **Step 7: Test ETL workflow manually**

Go to Actions → ETL Pipeline → Run workflow. Verify it completes.

- [ ] **Step 8: Commit any fixes**

```bash
git add -A
git commit -m "fix: adjustments from first real ETL run"
```

---

## Verification Checklist

After all tasks are complete, verify:

- [ ] `ruff check .` passes with zero errors
- [ ] `ruff format --check .` passes
- [ ] `python -m pytest tests/ -v` — all tests pass
- [ ] Supabase `matches` table has ~50K rows with normalized team names
- [ ] GitHub Actions CI workflow runs on push
- [ ] GitHub Actions ETL workflow can be triggered manually
- [ ] `.env` is in `.gitignore` and NOT committed
