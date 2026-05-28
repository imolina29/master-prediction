CREATE TABLE IF NOT EXISTS notification_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    notification_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    sent_date DATE NOT NULL DEFAULT CURRENT_DATE,
    picks_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_log_unique
    ON notification_log(notification_type, channel, sent_date);

ALTER TABLE notification_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on notification_log"
    ON notification_log FOR ALL
    USING (auth.role() = 'service_role');
