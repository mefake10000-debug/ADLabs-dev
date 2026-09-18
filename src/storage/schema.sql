-- AD Labs EdgeSight SQLite Local Cache Schema

CREATE TABLE IF NOT EXISTS store_rollups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    timestamp_start TEXT NOT NULL,
    timestamp_end TEXT NOT NULL,
    in_count INTEGER DEFAULT 0,
    out_count INTEGER DEFAULT 0,
    current_occupancy INTEGER DEFAULT 0,
    avg_dwell_seconds REAL DEFAULT 0.0,
    queue_length INTEGER DEFAULT 0,
    avg_queue_wait_seconds REAL DEFAULT 0.0,
    queue_alert_active INTEGER DEFAULT 0,
    exported INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS camera_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id TEXT NOT NULL,
    status TEXT NOT NULL,
    fps REAL DEFAULT 0.0,
    dropped_frames INTEGER DEFAULT 0,
    latency_ms REAL DEFAULT 0.0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crossing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    wire_id TEXT NOT NULL,
    track_id INTEGER NOT NULL,
    direction TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    exported INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rollups_exported ON store_rollups (exported);
CREATE INDEX IF NOT EXISTS idx_events_exported ON crossing_events (exported);

