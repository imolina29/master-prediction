-- backend/db/schema_xg.sql

CREATE TABLE IF NOT EXISTS match_xg (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    division TEXT NOT NULL,
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_xg REAL NOT NULL,
    away_xg REAL NOT NULL,
    home_goals SMALLINT,
    away_goals SMALLINT,
    source TEXT NOT NULL DEFAULT 'understat',
    UNIQUE(division, match_date, home_team, away_team)
);

CREATE INDEX IF NOT EXISTS idx_match_xg_date ON match_xg(match_date);
CREATE INDEX IF NOT EXISTS idx_match_xg_division ON match_xg(division);
