CREATE TABLE IF NOT EXISTS value_bets (
    id BIGSERIAL PRIMARY KEY,
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    division TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    model_prob REAL NOT NULL,
    implied_prob REAL NOT NULL,
    edge REAL NOT NULL,
    odd REAL NOT NULL,
    bookmaker TEXT,
    stake INTEGER NOT NULL,
    expected_value REAL NOT NULL,
    confidence TEXT NOT NULL,
    model_variant TEXT NOT NULL,
    result TEXT,
    profit REAL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    UNIQUE(match_date, home_team, away_team, market)
);

CREATE INDEX IF NOT EXISTS idx_value_bets_date ON value_bets(match_date);
CREATE INDEX IF NOT EXISTS idx_value_bets_result ON value_bets(result);
CREATE INDEX IF NOT EXISTS idx_value_bets_pending ON value_bets(result) WHERE result IS NULL;
