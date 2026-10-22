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
    -- Engagement analytics (head-pose + body behaviour)
    avg_attention_score REAL DEFAULT 0.0,
    facing_ratio REAL DEFAULT 0.0,
    phone_usage_rate REAL DEFAULT 0.0,
    engaged_ratio REAL DEFAULT 0.0,
    -- Social grouping (track co-proximity)
    group_count INTEGER DEFAULT 0,
    people_in_groups INTEGER DEFAULT 0,
    -- k-anonymous population cohorts, serialised as JSON
    demographics_json TEXT DEFAULT '',
    exported INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_interest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    category TEXT NOT NULL,
    viewers INTEGER DEFAULT 0,
    detections INTEGER DEFAULT 0,
    total_dwell_seconds REAL DEFAULT 0.0,
    avg_dwell_seconds REAL DEFAULT 0.0,
    timestamp_start TEXT NOT NULL,
    timestamp_end TEXT NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_products_exported ON product_interest (exported);
CREATE INDEX IF NOT EXISTS idx_products_camera ON product_interest (camera_id, category);

