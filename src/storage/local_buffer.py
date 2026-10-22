import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

class LocalBuffer:
    def __init__(self, db_path: str = "data/storage/edgesight.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        conn = self._get_connection()
        try:
            with conn:
                conn.executescript(schema_sql)
                self._migrate(conn)
        finally:
            conn.close()

    # Columns added after the first release. `CREATE TABLE IF NOT EXISTS` silently keeps
    # an existing table's original shape, so an edge node upgraded in place would hit
    # "no such column" on the first enriched rollup. This adds them idempotently.
    _MIGRATIONS = [
        ("store_rollups", "avg_attention_score", "REAL DEFAULT 0.0"),
        ("store_rollups", "facing_ratio", "REAL DEFAULT 0.0"),
        ("store_rollups", "phone_usage_rate", "REAL DEFAULT 0.0"),
        ("store_rollups", "engaged_ratio", "REAL DEFAULT 0.0"),
        ("store_rollups", "group_count", "INTEGER DEFAULT 0"),
        ("store_rollups", "people_in_groups", "INTEGER DEFAULT 0"),
        ("store_rollups", "demographics_json", "TEXT DEFAULT ''"),
    ]

    def _migrate(self, conn: sqlite3.Connection):
        for table, column, decl in self._MIGRATIONS:
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if not existing:
                continue
            if column in existing:
                continue
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

    def save_rollup(self, rollup: Dict[str, Any]) -> int:
        query = """
        INSERT INTO store_rollups (
            store_id, device_id, camera_id, timestamp_start, timestamp_end,
            in_count, out_count, current_occupancy, avg_dwell_seconds,
            queue_length, avg_queue_wait_seconds, queue_alert_active,
            avg_attention_score, facing_ratio, phone_usage_rate, engaged_ratio,
            group_count, people_in_groups, demographics_json, exported
        ) VALUES (
            :store_id, :device_id, :camera_id, :timestamp_start, :timestamp_end,
            :in_count, :out_count, :current_occupancy, :avg_dwell_seconds,
            :queue_length, :avg_queue_wait_seconds, :queue_alert_active,
            :avg_attention_score, :facing_ratio, :phone_usage_rate, :engaged_ratio,
            :group_count, :people_in_groups, :demographics_json, 0
        )
        """
        payload = dict(rollup)
        payload.setdefault("avg_attention_score", 0.0)
        payload.setdefault("facing_ratio", 0.0)
        payload.setdefault("phone_usage_rate", 0.0)
        payload.setdefault("engaged_ratio", 0.0)
        payload.setdefault("group_count", 0)
        payload.setdefault("people_in_groups", 0)
        payload.setdefault("demographics_json", "")
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(query, payload)
                return cursor.lastrowid
        finally:
            conn.close()

    def get_unexported_rollups(self, limit: int = 50) -> List[Dict[str, Any]]:
        query = """
        SELECT * FROM store_rollups
        WHERE exported = 0
        ORDER BY id ASC
        LIMIT ?
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(query, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def mark_as_exported(self, rollup_ids: List[int]):
        if not rollup_ids:
            return
        placeholders = ",".join("?" for _ in rollup_ids)
        query = f"UPDATE store_rollups SET exported = 1 WHERE id IN ({placeholders})"
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(query, rollup_ids)
        finally:
            conn.close()

    def save_event(self, event: Dict[str, Any]) -> int:
        query = """
        INSERT INTO crossing_events (
            store_id, device_id, camera_id, wire_id, track_id, direction, event_timestamp, exported
        ) VALUES (
            :store_id, :device_id, :camera_id, :wire_id, :track_id, :direction, :event_timestamp, 0
        )
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(query, event)
                return cursor.lastrowid
        finally:
            conn.close()

    def get_unexported_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        query = """
        SELECT * FROM crossing_events
        WHERE exported = 0
        ORDER BY id ASC
        LIMIT ?
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(query, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def mark_events_as_exported(self, event_ids: List[int]):
        if not event_ids:
            return
        placeholders = ",".join("?" for _ in event_ids)
        query = f"UPDATE crossing_events SET exported = 1 WHERE id IN ({placeholders})"
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(query, event_ids)
        finally:
            conn.close()

    def log_camera_health(self, camera_id: str, status: str, fps: float, dropped: int, latency_ms: float):
        query = """
        INSERT INTO camera_health (camera_id, status, fps, dropped_frames, latency_ms)
        VALUES (?, ?, ?, ?, ?)
        """
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(query, (camera_id, status, fps, dropped, latency_ms))
        finally:
            conn.close()

    def save_product_interest(self, record: Dict[str, Any]) -> int:
        query = """
        INSERT INTO product_interest (
            store_id, device_id, camera_id, category, viewers, detections,
            total_dwell_seconds, avg_dwell_seconds, timestamp_start, timestamp_end, exported
        ) VALUES (
            :store_id, :device_id, :camera_id, :category, :viewers, :detections,
            :total_dwell_seconds, :avg_dwell_seconds, :timestamp_start, :timestamp_end, 0
        )
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(query, record)
                return cursor.lastrowid
        finally:
            conn.close()

    def get_unexported_products(self, limit: int = 200) -> List[Dict[str, Any]]:
        query = """
        SELECT * FROM product_interest
        WHERE exported = 0
        ORDER BY id ASC
        LIMIT ?
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def mark_products_as_exported(self, product_ids: List[int]):
        if not product_ids:
            return
        placeholders = ",".join("?" for _ in product_ids)
        query = f"UPDATE product_interest SET exported = 1 WHERE id IN ({placeholders})"
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(query, product_ids)
        finally:
            conn.close()
