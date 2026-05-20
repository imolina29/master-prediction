-- backend/db/schema.sql

-- Competitions (leagues + tournaments)
CREATE TABLE IF NOT EXISTS competitions (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL
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
    canonical_name TEXT PRIMARY KEY,
    short_name TEXT,
    country TEXT
);

-- Team name aliases (variant -> canonical)
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
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_elo REAL,
    away_elo REAL,
    home_form3 REAL,
    home_form5 REAL,
    away_form3 REAL,
    away_form5 REAL,
    ft_home_goals SMALLINT,
    ft_away_goals SMALLINT,
    ft_result CHAR(1),
    ht_home_goals SMALLINT,
    ht_away_goals SMALLINT,
    ht_result CHAR(1),
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
    UNIQUE(division, match_date, home_team, away_team)
);

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_division ON matches(division);
CREATE INDEX IF NOT EXISTS idx_matches_home ON matches(home_team);
CREATE INDEX IF NOT EXISTS idx_matches_away ON matches(away_team);
