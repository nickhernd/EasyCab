CREATE TABLE IF NOT EXISTS taxis (
    taxi_id INTEGER PRIMARY KEY,
    public_key TEXT,
    registration_token TEXT,
    status TEXT,
    registered_at TIMESTAMP,
    last_updated TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_taxi_status ON taxis(status);
CREATE INDEX IF NOT EXISTS idx_taxi_registered ON taxis(registered_at);