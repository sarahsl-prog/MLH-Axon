CREATE TABLE IF NOT EXISTS traffic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    path TEXT NOT NULL,
    method TEXT NOT NULL,
    ip TEXT NOT NULL,
    country TEXT,
    user_agent TEXT,
    prediction TEXT NOT NULL,
    confidence REAL NOT NULL,
    bot_score INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_timestamp ON traffic(timestamp);
CREATE INDEX idx_prediction ON traffic(prediction);
