CREATE TABLE IF NOT EXISTS claims (
    id SERIAL PRIMARY KEY,
    claim TEXT NOT NULL,
    label TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
