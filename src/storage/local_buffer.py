import sqlite3
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

class LocalBuffer:
    def __init__(self, db_path: str = "data/storage/edgesight.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA busy_timeout=10000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        conn = self._get_connection()
        try:
            conn.execute("PRAGMA journal_mode=WAL")
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
        for table in ("store_rollups", "crossing_events", "product_interest"):
            columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if "record_id" not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN record_id TEXT")
            conn.execute(f"UPDATE {table} SET record_id=lower(hex(randomblob(16))) WHERE record_id IS NULL")
            conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table}_record_id ON {table}(record_id)")
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
            group_count, people_in_groups, demographics_json, record_id, exported
        ) VALUES (
            :store_id, :device_id, :camera_id, :timestamp_start, :timestamp_end,
            :in_count, :out_count, :current_occupancy, :avg_dwell_seconds,
            :queue_length, :avg_queue_wait_seconds, :queue_alert_active,
            :avg_attention_score, :facing_ratio, :phone_usage_rate, :engaged_ratio,
            :group_count, :people_in_groups, :demographics_json, :record_id, 0
        )
        """
        payload = dict(rollup)
        payload["record_id"] = uuid.uuid4().hex
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
            store_id, device_id, camera_id, wire_id, track_id, direction, event_timestamp, record_id, exported
        ) VALUES (
            :store_id, :device_id, :camera_id, :wire_id, :track_id, :direction, :event_timestamp, :record_id, 0
        )
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(query, dict(event, record_id=uuid.uuid4().hex))
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
            total_dwell_seconds, avg_dwell_seconds, timestamp_start, timestamp_end, record_id, exported
        ) VALUES (
            :store_id, :device_id, :camera_id, :category, :viewers, :detections,
            :total_dwell_seconds, :avg_dwell_seconds, :timestamp_start, :timestamp_end, :record_id, 0
        )
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(query, dict(record, record_id=uuid.uuid4().hex))
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

    def get_recent_products_top(
        self, camera_id: str, limit: int = 8
    ) -> List[Dict[str, Any]]:
        """Aggregate product_interest rows for live_snapshot products_top (not POS SKUs)."""
        query = """
        SELECT category,
               SUM(viewers) AS viewers,
               SUM(detections) AS detections,
               AVG(avg_dwell_seconds) AS avg_dwell_seconds
        FROM product_interest
        WHERE camera_id = ?
        GROUP BY category
        ORDER BY SUM(viewers) DESC, SUM(detections) DESC
        LIMIT ?
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(query, (camera_id, limit))
            rows = []
            for row in cursor.fetchall():
                rows.append({
                    "category": row["category"],
                    "viewers": int(row["viewers"] or 0),
                    "detections": int(row["detections"] or 0),
                    "avg_dwell_seconds": round(float(row["avg_dwell_seconds"] or 0.0), 1),
                })
            return rows
        except Exception:
            return []
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

    def maintenance(self, retention_days: int = 7) -> int:
        """Prune acknowledged history only; pending records are never evicted."""
        if retention_days < 1:
            raise ValueError("retention_days must be positive")
        conn = self._get_connection()
        deleted = 0
        try:
            with conn:
                for table in ("store_rollups", "crossing_events", "product_interest"):
                    cursor = conn.execute(f"DELETE FROM {table} WHERE exported=1 AND created_at < datetime('now', ?)", (f"-{retention_days} days",))
                    deleted += cursor.rowcount
                conn.execute("DELETE FROM camera_health WHERE timestamp < datetime('now', ?)", (f"-{retention_days} days",))
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            return deleted
        finally:
            conn.close()

    def backlog_stats(self) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            pending = 0
            oldest = None
            for table in ("store_rollups", "crossing_events", "product_interest"):
                count, stamp = conn.execute(f"SELECT count(*), min(created_at) FROM {table} WHERE exported=0").fetchone()
                pending += count
                if stamp and (oldest is None or stamp < oldest):
                    oldest = stamp
            return {"pending_records": pending, "oldest_pending_at": oldest}
        finally:
            conn.close()
