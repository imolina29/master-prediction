CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    division TEXT NOT NULL,
    model_variant TEXT NOT NULL,
    prob_home REAL,
    prob_draw REAL,
    prob_away REAL,
    prob_over25 REAL,
    prob_btts REAL,
    predicted_result TEXT,
    confidence TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(match_date, home_team, away_team)
);

CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(match_date);
CREATE INDEX IF NOT EXISTS idx_predictions_division ON predictions(division);
