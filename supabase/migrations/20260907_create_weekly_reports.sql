CREATE TABLE IF NOT EXISTS weekly_reports (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    week_start date NOT NULL,
    week_end date NOT NULL,
    total_predictions int DEFAULT 0,
    total_hits int DEFAULT 0,
    hit_rate numeric(5,3) DEFAULT 0,
    stats jsonb,
    narrative text,
    created_at timestamptz DEFAULT now(),
    UNIQUE(week_start)
);
