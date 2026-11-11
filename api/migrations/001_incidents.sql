CREATE SCHEMA IF NOT EXISTS sentinel;

CREATE TABLE IF NOT EXISTS sentinel.feed_batches (
    fetched_at timestamptz PRIMARY KEY,
    item_count integer NOT NULL CHECK (item_count >= 0)
);

CREATE TABLE IF NOT EXISTS sentinel.incidents (
    id text PRIMARY KEY,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    content_hash text NOT NULL
);

CREATE TABLE IF NOT EXISTS sentinel.incident_versions (
    incident_id text NOT NULL REFERENCES sentinel.incidents(id),
    observed_at timestamptz NOT NULL REFERENCES sentinel.feed_batches(fetched_at),
    payload jsonb NOT NULL,
    PRIMARY KEY (incident_id, observed_at)
);
