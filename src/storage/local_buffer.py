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
        finally:
            conn.close()

    def save_rollup(self, rollup: Dict[str, Any]) -> int:
        query = """
        INSERT INTO store_rollups (
            store_id, device_id, camera_id, timestamp_start, timestamp_end,
            in_count, out_count, current_occupancy, avg_dwell_seconds,
            queue_length, avg_queue_wait_seconds, queue_alert_active, exported
        ) VALUES (
            :store_id, :device_id, :camera_id, :timestamp_start, :timestamp_end,
            :in_count, :out_count, :current_occupancy, :avg_dwell_seconds,
            :queue_length, :avg_queue_wait_seconds, :queue_alert_active, 0
        )
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(query, rollup)
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
