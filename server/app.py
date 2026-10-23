import os
import re
import secrets
import sqlite3
import sys
import time
import json
import logging
from typing import List, Dict, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("EdgeSight-API")
app = FastAPI(title="AD Labs EdgeSight Enterprise Platform", version="2.0.0")


# Allow the Next.js marketing dashboard (localhost:3000) to call EdgeSight directly
# when operators bypass the site's /api/edgesight proxy. Override via EDGESIGHT_CORS_ORIGINS.
_cors_origins = [
    o.strip()
    for o in os.environ.get(
        "EDGESIGHT_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    # POST needed for NFC tap webhook + telemetry/config writes from the portal.
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-API-Key"],
)

from server.nfc_store import (
    industry_status_block,
    nfc_live_block,
    record_tap,
    retail_roles_block,
)
try:
    from src.analytics.journey import build_journey_block, zones_from_snapshot_rows
except ImportError:
    # cloud-dashboard image mounts ./server only — journey helpers live under ./src.
    def zones_from_snapshot_rows(rows):  # type: ignore[misc]
        return []

    def build_journey_block(zone_rows=None):  # type: ignore[misc]
        return {
            "status": "PARTIAL",
            "badge_copy": "Journey block needs edge src mount or live snapshot journey.",
            "stages": [],
            "dead_zones": [],
        }


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.environ.get("SERVER_DB_PATH", "data/storage/cloud_metrics.db")
CONFIG_PATH = os.environ.get("CAMERAS_CONFIG", "configs/cameras.yaml")
VIDEO_DIR = os.environ.get("SAMPLE_VIDEOS_DIR", "data/sample_videos")
VIDEO_EXTS = (".mp4", ".avi", ".mov", ".mkv")
STREAM_PREFIXES = ("rtsp://", "rtsps://", "http://")

# Optional shared-secret protection for state-changing calls (telemetry ingestion, config writes,
# metrics reset). Unset by default -- today's zero-config workflow is unchanged unless an operator
# explicitly sets EDGESIGHT_API_KEY. GET endpoints (occupancy reads, live stream, snapshots) stay
# open, matching the dashboard's own read access; real per-user auth is future work, not this.
API_KEY = os.environ.get("EDGESIGHT_API_KEY")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.middleware("http")
async def require_api_key_for_writes(request: Request, call_next):
    if API_KEY and request.method != "GET" and request.url.path.startswith("/api/v1/"):
        provided = request.headers.get("x-api-key")
        if not provided or not secrets.compare_digest(provided, API_KEY):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid X-API-Key header"})
    return await call_next(request)

def _redact_source(source: Optional[str]) -> Optional[str]:
    """Masks embedded RTSP credentials (rtsp://user:pass@host/...) before a camera config is
    ever returned in an API response. GET endpoints have no auth (see API_KEY above), so this
    is the only thing standing between an exposed port and a leaked camera password."""
    if not source:
        return source
    return re.sub(r'(rtsps?://)[^@/\s]+@', r'\1****:****@', source)

def _redact_camera(cam: Dict[str, Any]) -> Dict[str, Any]:
    if "source" not in cam:
        return cam
    redacted = dict(cam)
    redacted["source"] = _redact_source(redacted["source"])
    return redacted

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_rollups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            device_id TEXT,
            camera_id TEXT,
            timestamp_start TEXT,
            timestamp_end TEXT,
            in_count INTEGER,
            out_count INTEGER,
            current_occupancy INTEGER,
            avg_dwell_seconds REAL,
            queue_length INTEGER,
            avg_queue_wait_seconds REAL,
            queue_alert_active INTEGER,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            device_id TEXT,
            camera_id TEXT,
            wire_id TEXT,
            track_id INTEGER,
            direction TEXT,
            event_timestamp TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_rollups_store_camera ON telemetry_rollups (store_id, camera_id, id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rollups_store_received_cover ON telemetry_rollups "
                     "(store_id, received_at, camera_id, in_count, out_count, avg_dwell_seconds)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rollups_store_id ON telemetry_rollups (store_id, id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_store_camera ON telemetry_events (store_id, camera_id, id)")

        # Enrichment columns (engagement / groups / demographics) are added by
        # migration rather than by editing the CREATE above, so an existing cloud
        # database keeps its rows.
        _add_column(conn, "telemetry_rollups", "avg_attention_score", "REAL")
        _add_column(conn, "telemetry_rollups", "facing_ratio", "REAL")
        _add_column(conn, "telemetry_rollups", "phone_usage_rate", "REAL")
        _add_column(conn, "telemetry_rollups", "engaged_ratio", "REAL")
        _add_column(conn, "telemetry_rollups", "group_count", "INTEGER")
        _add_column(conn, "telemetry_rollups", "people_in_groups", "INTEGER")
        _add_column(conn, "telemetry_rollups", "demographics_json", "TEXT")
        _add_column(conn, "telemetry_rollups", "loop_count", "INTEGER DEFAULT 0")
        _add_column(conn, "telemetry_rollups", "is_simulated", "INTEGER DEFAULT 0")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS device_registry (
            device_id TEXT PRIMARY KEY,
            device_name TEXT,
            inference_engine TEXT,
            perf_mode TEXT,
            cameras INTEGER,
            python_version TEXT,
            torch_version TEXT,
            registered_at TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_state (
            rule_id TEXT,
            camera_id TEXT,
            state TEXT,
            last_change_at TEXT,
            PRIMARY KEY (rule_id, camera_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            device_id TEXT,
            camera_id TEXT,
            category TEXT,
            viewers INTEGER,
            detections INTEGER,
            total_dwell_seconds REAL,
            avg_dwell_seconds REAL,
            timestamp_start TEXT,
            timestamp_end TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

def _add_column(conn, table: str, column: str, column_type: str):
    """Adds a column if it is missing. Safe to run on every boot."""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

init_db()

class RollupItem(BaseModel):
    id: Optional[int] = None
    store_id: str
    device_id: str
    camera_id: str
    timestamp_start: str
    timestamp_end: str
    in_count: int
    out_count: int
    current_occupancy: int
    avg_dwell_seconds: float
    queue_length: int
    avg_queue_wait_seconds: float
    queue_alert_active: int
    # Enrichment tier. All optional: an edge node running the fast tier only will
    # send nulls here.
    avg_attention_score: Optional[float] = None
    facing_ratio: Optional[float] = None
    phone_usage_rate: Optional[float] = None
    engaged_ratio: Optional[float] = None
    group_count: Optional[int] = None
    people_in_groups: Optional[int] = None
    demographics_json: Optional[str] = None
    # Sample-video provenance (loop_count > 0 => replaying sample footage, not live RTSP)
    loop_count: Optional[int] = 0
    is_simulated: Optional[int] = 0

class TelemetryPayload(BaseModel):
    batch_size: int
    rollups: List[RollupItem]
    exported_at: float

class EventItem(BaseModel):
    id: Optional[int] = None
    store_id: str
    device_id: str
    camera_id: str
    wire_id: str
    track_id: int
    direction: str
    event_timestamp: str

class EventBatchPayload(BaseModel):
    batch_size: int
    events: List[EventItem]
    exported_at: float

class ProductInterestItem(BaseModel):
    """One category's interest over one rollup window.

    This is an aggregate: a category name, how many distinct shoppers were near it,
    how many times it was detected and how long they lingered. There is no face,
    no image and no person-level row anywhere in this payload.
    """
    id: Optional[int] = None
    store_id: str
    device_id: str
    camera_id: str
    category: str
    viewers: int
    detections: int
    total_dwell_seconds: float
    avg_dwell_seconds: float
    timestamp_start: str
    timestamp_end: str

class ProductBatchPayload(BaseModel):
    batch_size: int
    products: List[ProductInterestItem]
    exported_at: float


class NfcTapPayload(BaseModel):
    """Fashion / apparel NFC reader webhook — one person tap on a tagged product."""

    product_id: str = Field(..., min_length=1, max_length=128)
    zone: Optional[str] = Field(default=None, max_length=128)
    zone_id: Optional[str] = Field(default=None, max_length=64)
    camera_id: Optional[str] = Field(default=None, max_length=64)
    tapped_at: Optional[str] = Field(default=None, max_length=64)
    meta: Optional[Dict[str, Any]] = None

    @field_validator("product_id")
    @classmethod
    def _strip_product(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("product_id is required")
        return s

# Web App Entrypoint (Structured Production SPA)
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # If EDGESIGHT_API_KEY is set, the Calibration Studio's own POST calls (save calibration,
    # switch source, reset metrics) need to send it too. Embedding it in the page means it's
    # visible in page source to anyone who can load this page -- acceptable as a barrier against
    # unauthenticated internet scanners hitting an exposed port, not a substitute for real
    # per-user login (out of scope here).
    return templates.TemplateResponse(request=request, name="index.html", context={"api_key": API_KEY or ""})

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AD Labs EdgeSight Enterprise API", "timestamp": time.time()}

# Telemetry Sync Endpoint
@app.post("/api/v1/telemetry")
def receive_telemetry(payload: TelemetryPayload):
    with sqlite3.connect(DB_PATH) as conn:
        for r in payload.rollups:
            conn.execute("""
            INSERT INTO telemetry_rollups (
                store_id, device_id, camera_id, timestamp_start, timestamp_end,
                in_count, out_count, current_occupancy, avg_dwell_seconds,
                queue_length, avg_queue_wait_seconds, queue_alert_active,
                avg_attention_score, facing_ratio, phone_usage_rate, engaged_ratio,
                group_count, people_in_groups, demographics_json,
                loop_count, is_simulated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.store_id, r.device_id, r.camera_id, r.timestamp_start, r.timestamp_end,
                r.in_count, r.out_count, r.current_occupancy, r.avg_dwell_seconds,
                r.queue_length, r.avg_queue_wait_seconds, r.queue_alert_active,
                r.avg_attention_score, r.facing_ratio, r.phone_usage_rate, r.engaged_ratio,
                r.group_count, r.people_in_groups, r.demographics_json,
                r.loop_count or 0, r.is_simulated or 0
            ))
        conn.commit()
    return {"status": "success", "processed_records": len(payload.rollups)}

# Product Interest Sync Endpoint (per-category aggregates, no person-level data)
@app.post("/api/v1/telemetry/products")
def receive_products(payload: ProductBatchPayload):
    with sqlite3.connect(DB_PATH) as conn:
        for p in payload.products:
            conn.execute("""
            INSERT INTO telemetry_products (
                store_id, device_id, camera_id, category, viewers, detections,
                total_dwell_seconds, avg_dwell_seconds, timestamp_start, timestamp_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.store_id, p.device_id, p.camera_id, p.category, p.viewers, p.detections,
                p.total_dwell_seconds, p.avg_dwell_seconds, p.timestamp_start, p.timestamp_end
            ))
        conn.commit()
    return {"status": "success", "processed_records": len(payload.products)}

# Per-Crossing Event Sync Endpoint (durable, independent of rollup aggregation)
@app.post("/api/v1/telemetry/events")
def receive_events(payload: EventBatchPayload):
    with sqlite3.connect(DB_PATH) as conn:
        for e in payload.events:
            conn.execute("""
            INSERT INTO telemetry_events (
                store_id, device_id, camera_id, wire_id, track_id, direction, event_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                e.store_id, e.device_id, e.camera_id, e.wire_id, e.track_id, e.direction, e.event_timestamp
            ))
        conn.commit()
    return {"status": "success", "processed_records": len(payload.events)}

# Individually Queryable Crossing Events (audit trail, independent of rollups)
@app.get("/api/v1/events")
def get_events(store_id: str = "store_mumbai_001", camera_id: Optional[str] = None, limit: int = 100):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM telemetry_events WHERE store_id = ?"
        params: List[Any] = [store_id]
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return {"events": [dict(r) for r in reversed(rows)]}

def _live_dir() -> str:
    return os.path.join(os.path.dirname(DB_PATH), "live")


def _read_live_snapshot(camera_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Frame-synced JSON written by edge-analyzer (matches YOLO overlay people counts)."""
    live_dir = _live_dir()
    path = os.path.join(live_dir, f"{camera_id}.json" if camera_id else "store.json")
    if not os.path.exists(path):
        if camera_id:
            return None
        if not os.path.isdir(live_dir):
            return None
        for name in sorted(os.listdir(live_dir)):
            if name.endswith(".json") and not name.endswith(".tmp.json") and name != "store.json":
                path = os.path.join(live_dir, name)
                break
        else:
            return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        ts = data.get("timestamp")
        if ts:
            try:
                age = time.time() - time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S"))
                if age > 15:
                    data["_stale"] = True
            except Exception:
                pass
        return data
    except Exception:
        return None


def _lifetime_product_rollup(rows: Any, people_now: int) -> bool:
    """True when products_top is an all-time SQL sum, not this frame.

    Frame interest stays near the people on camera. Lifetime rollups are 10^4–10^5
    viewers and must not be served as a live KPI.
    """
    if not isinstance(rows, list) or not rows:
        return False
    viewers = 0
    detections = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            viewers = max(viewers, int(row.get("viewers") or 0))
            detections = max(detections, int(row.get("detections") or 0))
        except (TypeError, ValueError):
            continue
    cap = max(int(people_now or 0), 1) * 50
    return viewers > max(cap, 200) or detections > max(cap * 4, 800)


def _bind_live_cv(result: Dict[str, Any], cam_rows: List[Dict[str, Any]]) -> None:
    """Present = active track ids. In/Out = session tripwire counts.

    Store snapshots omit track_ids. Cam files have them. Never substitute the
    SQLite day SUM when a fresh snapshot is the source.
    """
    if result.get("source") != "live_snapshot" or not cam_rows:
        return
    track_ids: List[Any] = []
    seen = set()
    saw_track_key = False
    tripwires: List[Dict[str, Any]] = []
    for row in cam_rows:
        raw_ids = row.get("track_ids")
        if isinstance(raw_ids, list):
            saw_track_key = True
            for tid in raw_ids:
                if tid in seen:
                    continue
                seen.add(tid)
                track_ids.append(tid)
        for tw in row.get("tripwires") or []:
            if isinstance(tw, dict):
                item = dict(tw)
                item.setdefault("camera_id", row.get("camera_id"))
                tripwires.append(item)
        # Cam snapshot totals are tripwire session counts even when the array
        # is absent for a beat (file replace). They are never the day SUM.
        if not row.get("tripwires") and (
            "session_in" in row or "total_visitors" in row or "session_out" in row or "total_exits" in row
        ):
            inn_raw = row.get("session_in") if row.get("session_in") is not None else row.get("total_visitors")
            out_raw = row.get("session_out") if row.get("session_out") is not None else row.get("total_exits")
            tripwires.append({
                "id": "snapshot_session",
                "name": "Session",
                "camera_id": row.get("camera_id"),
                "in_count": int(inn_raw or 0),
                "out_count": int(out_raw or 0),
            })
    if saw_track_key:
        result["track_ids"] = track_ids
        result["active_tracks"] = len(track_ids)
        result["people_now"] = len(track_ids)
        result["net_occupancy"] = len(track_ids)
        result["present_binding"] = "active_tracks"
    if tripwires:
        inn = sum(int(t.get("in_count") or 0) for t in tripwires)
        out = sum(int(t.get("out_count") or 0) for t in tripwires)
        result["tripwires"] = tripwires
        result["total_visitors"] = inn
        result["total_exits"] = out
        result["session_in"] = inn
        result["session_out"] = out
        result["inout_binding"] = "session_tripwire"
    people = int(result.get("people_now") or 0)
    if _lifetime_product_rollup(result.get("products_top"), people):
        result["products_top"] = None
        result["products_top_withheld"] = "lifetime_rollup"
    models = result.get("models") or {}
    if isinstance(models, dict) and models.get("enrichment") is False:
        result["engagement"] = None


# Live Store Telemetry
@app.get("/api/v1/live")
def get_live_metrics(store_id: str = "store_mumbai_001", camera_id: Optional[str] = None):
    snap = _read_live_snapshot(camera_id)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # One row per camera: each camera's own most recent rollup. With camera_id given this
        # is naturally at most one row; without it, reading a single global "latest" row would
        # report whichever camera happened to sync last, not a true store-wide figure.
        if camera_id:
            latest_rows = conn.execute(
                "SELECT * FROM telemetry_rollups WHERE store_id = ? AND camera_id = ? ORDER BY id DESC LIMIT 1",
                (store_id, camera_id)
            ).fetchall()
        else:
            latest_rows = conn.execute("""
            SELECT t1.* FROM telemetry_rollups t1
            INNER JOIN (
                SELECT camera_id, MAX(id) AS max_id FROM telemetry_rollups WHERE store_id = ? GROUP BY camera_id
            ) t2 ON t1.camera_id = t2.camera_id AND t1.id = t2.max_id
            """, (store_id,)).fetchall()

        live_people_count = sum(r["current_occupancy"] for r in latest_rows)
        queue_length = sum(r["queue_length"] for r in latest_rows)
        queue_alert_active = any(r["queue_alert_active"] for r in latest_rows)
        avg_queue_wait_seconds = round(sum(r["avg_queue_wait_seconds"] for r in latest_rows) / len(latest_rows), 1) if latest_rows else 0.0
        latest_avg_dwell_fallback = round(sum(r["avg_dwell_seconds"] for r in latest_rows) / len(latest_rows), 1) if latest_rows else 0.0
        latest_in_count_fallback = sum(r["in_count"] for r in latest_rows)

        # Aggregated totals today (filtering by current date so old test data doesn't pollute counts).
        # Already sums across every camera's rows for the day when camera_id is None -- unaffected by
        # the single-row problem above.
        footfall_query = """
        SELECT SUM(in_count) as total_visitors, SUM(out_count) as total_exits, AVG(avg_dwell_seconds) as avg_dwell
        FROM telemetry_rollups
        WHERE store_id = ? AND date(received_at) = date('now')
          AND (
              COALESCE(is_simulated, 0) = 0
              OR loop_count = (
                  SELECT MAX(r2.loop_count)
                  FROM telemetry_rollups r2
                  WHERE r2.store_id = telemetry_rollups.store_id
                    AND r2.camera_id = telemetry_rollups.camera_id
                    AND date(r2.received_at) = date('now')
                    AND COALESCE(r2.is_simulated, 0) = 1
              )
          )
        """
        footfall_params: List[Any] = [store_id]
        if camera_id:
            footfall_query += " AND camera_id = ?"
            footfall_params.append(camera_id)
        row_footfall = conn.execute(footfall_query, footfall_params).fetchone()

        total_in = row_footfall["total_visitors"] if row_footfall and row_footfall["total_visitors"] is not None else 0
        total_out = row_footfall["total_exits"] if row_footfall and row_footfall["total_exits"] is not None else 0
        avg_dwell = round(row_footfall["avg_dwell"], 1) if row_footfall and row_footfall["avg_dwell"] is not None else latest_avg_dwell_fallback

        # Fallback if no records today yet
        if total_in == 0 and latest_rows:
            total_in = latest_in_count_fallback

        # Per-camera freshness for multi-cam honesty (store occupancy still SUMs cams —
        # not deduplicated until ReID + handoff fusion + consensus ship).
        per_camera = []
        for r in latest_rows:
            per_camera.append({
                "camera_id": r["camera_id"],
                "occupancy": r["current_occupancy"],
                "queue_length": r["queue_length"],
                "avg_dwell_seconds": r["avg_dwell_seconds"],
                "in_count": r["in_count"],
                "out_count": r["out_count"],
                "last_rollup_at": r["timestamp_end"] if "timestamp_end" in r.keys() else r["received_at"],
            })

        result = {
            "store_id": store_id,
            "camera_id": camera_id,
            "total_visitors": total_in,
            "total_exits": total_out,
            "net_occupancy": live_people_count,
            "avg_dwell_seconds": avg_dwell,
            "queue_length": queue_length,
            "avg_queue_wait_seconds": avg_queue_wait_seconds,
            "queue_alert_active": queue_alert_active,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "occupancy_mode": "sum",
            "occupancy_note": "Store occupancy sums per-camera rollups; overlapping FOVs double-count until consensus ships.",
            "per_camera": per_camera,
            "source": "telemetry_rollups",
        }

        # Prefer frame-synced snapshot when fresh — numbers match the YOLO MJPEG HUD.
        # IMPORTANT: live tripwire totals may be 0 (no crossing this pass). Never use
        # `0 or db_rollup` — that resurrects day SUM (~200) and makes In/Out look fake.
        if snap and not snap.get("_stale"):
            def _snap_int(key: str, fallback: int) -> int:
                if key in snap and snap[key] is not None:
                    try:
                        return int(snap[key])
                    except (TypeError, ValueError):
                        return fallback
                return fallback

            def _snap_float(key: str, fallback: float) -> float:
                if key in snap and snap[key] is not None:
                    try:
                        return float(snap[key])
                    except (TypeError, ValueError):
                        return fallback
                return fallback

            result.update({
                "total_visitors": _snap_int("total_visitors", int(result["total_visitors"] or 0)),
                "total_exits": _snap_int("total_exits", int(result["total_exits"] or 0)),
                "net_occupancy": _snap_int(
                    "net_occupancy",
                    _snap_int("people_now", int(result["net_occupancy"] or 0)),
                ),
                "people_now": _snap_int("people_now", 0),
                "objects_now": _snap_int("objects_now", 0),
                "staff_now": _snap_int("staff_now", 0),
                "avg_dwell_seconds": _snap_float("avg_dwell_seconds", float(result["avg_dwell_seconds"] or 0)),
                "queue_length": _snap_int("queue_length", int(result["queue_length"] or 0)),
                "avg_queue_wait_seconds": _snap_float(
                    "avg_queue_wait_seconds",
                    float(result["avg_queue_wait_seconds"] or 0),
                ),
                "queue_alert_active": bool(snap.get("queue_alert_active", result["queue_alert_active"])),
                "infer_fps": snap.get("infer_fps"),
                "decode_fps": snap.get("decode_fps"),
                "display_fps": snap.get("display_fps"),
                "perf_mode": snap.get("perf_mode") or (snap.get("models") or {}).get("perf_mode"),
                "last_updated": snap.get("timestamp") or result["last_updated"],
                "source": "live_snapshot",
                "occupancy_mode": "active_tracks",
                "occupancy_note": (
                    "people_now = active person tracks only (objects are objects_now, not IDs). "
                    "Tripwire IN/OUT are session/pass totals from the live snapshot "
                    "(0 is real — not a day rollup). Multi-cam still sums cameras."
                ),
                "models": snap.get("models"),
                "engagement": snap.get("engagement"),
                "cameras": snap.get("cameras"),
                "reid": snap.get("reid"),
                "products_top": snap.get("products_top"),
                "zones": snap.get("zones"),
                "staff_zones": snap.get("staff_zones"),
                "queues": snap.get("queues"),
                "entrance": snap.get("entrance"),
                "stop_rate": snap.get("stop_rate"),
                "floor": snap.get("floor"),
                "staff": snap.get("staff"),
                "safety": snap.get("safety"),
                "alerts": snap.get("alerts"),
                "field_status": snap.get("field_status"),
                "journey": snap.get("journey"),
                "tripwires": snap.get("tripwires"),
                "tracks": snap.get("tracks"),
                "track_ids": snap.get("track_ids"),
                "session_in": _snap_int("session_in", _snap_int("total_visitors", 0)),
                "session_out": _snap_int("session_out", _snap_int("total_exits", 0)),
            })
        elif snap and snap.get("_stale"):
            result["snapshot_stale"] = True

        # Prefer per-camera rows from frame-synced files when present (fresher than rollups).
        # Skip cams not listed in store snapshot when max_cameras pruned the active set.
        live_dir = _live_dir()
        active_cams = set(snap.get("cameras") or []) if snap and not snap.get("_stale") else set()
        cam_payloads: List[Dict[str, Any]] = []
        if os.path.isdir(live_dir):
            snap_cams = []
            for name in sorted(os.listdir(live_dir)):
                if not name.endswith(".json") or name in ("store.json",) or name.endswith(".tmp.json"):
                    continue
                cam_key = name[: -len(".json")]
                if active_cams and cam_key not in active_cams:
                    continue
                try:
                    with open(os.path.join(live_dir, name)) as f:
                        row = json.load(f)
                except Exception:
                    continue
                if camera_id and row.get("camera_id") != camera_id:
                    continue
                cam_payloads.append(row)
                vl = (row.get("video_loop") or {})
                snap_cams.append({
                    "camera_id": row.get("camera_id"),
                    "occupancy": row.get("people_now", row.get("net_occupancy", 0)),
                    "queue_length": row.get("queue_length", 0),
                    "avg_dwell_seconds": row.get("avg_dwell_seconds", 0),
                    "in_count": row.get("total_visitors", 0),
                    "out_count": row.get("total_exits", 0),
                    "last_rollup_at": row.get("timestamp"),
                    "infer_fps": row.get("infer_fps"),
                    "loop_count": vl.get("loop_count"),
                    "is_simulated": vl.get("is_simulated"),
                    "unique_this_pass": vl.get("unique_this_pass"),
                    "unique_total_all_passes": vl.get("unique_total_all_passes"),
                    "source_fps": vl.get("source_fps"),
                    "counting_mode": vl.get("counting_mode"),
                    "source": "live_snapshot",
                })
            if snap_cams:
                result["per_camera"] = snap_cams
                video_loop_by_camera = {
                    row["camera_id"]: {
                        "loop_count": row.get("loop_count"),
                        "is_simulated": row.get("is_simulated"),
                        "unique_this_pass": row.get("unique_this_pass"),
                        "unique_total_all_passes": row.get("unique_total_all_passes"),
                        "source_fps": row.get("source_fps"),
                        "counting_mode": row.get("counting_mode"),
                    }
                    for row in snap_cams
                }
                result["video_loop_by_camera"] = video_loop_by_camera
                if camera_id and camera_id in video_loop_by_camera:
                    result["video_loop"] = video_loop_by_camera[camera_id]
                elif len(video_loop_by_camera) == 1:
                    result["video_loop"] = next(iter(video_loop_by_camera.values()))
                else:
                    # No singular loop state exists for a multi-camera store.
                    result["video_loop"] = None

        _bind_live_cv(result, cam_payloads)

        # NFC stub (optional hardware) + floor-role maturity. Industry vertical map is
        # deprecated alias only — Live hub features retail_roles, not fashion/etc tabs.
        fresh_snap = snap if snap and not snap.get("_stale") else None
        nfc = nfc_live_block(20)
        result["nfc"] = nfc
        result["retail_roles"] = retail_roles_block(fresh_snap, nfc)
        result["industry"] = industry_status_block(fresh_snap, nfc)  # deprecated

        # Service journey / dead-zones — always present with 0 defaults (never invent traction).
        if result.get("journey") is None:
            zone_rows = []
            if fresh_snap:
                zone_rows = zones_from_snapshot_rows([fresh_snap])
            result["journey"] = build_journey_block(zone_rows)

        # Frame-synced provenance for the portal (ISO timestamp + sample-loop state).
        result["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        result["video_loop"] = (snap or {}).get("video_loop")
        result["loop_count"] = ((snap or {}).get("video_loop") or {}).get("loop_count")
        result["is_simulated"] = ((snap or {}).get("video_loop") or {}).get("is_simulated")
        result["unique_this_pass"] = ((snap or {}).get("video_loop") or {}).get("unique_this_pass")
        result["unique_total_all_passes"] = ((snap or {}).get("video_loop") or {}).get("unique_total_all_passes")

        return result


@app.post("/api/v1/nfc/tap")
def post_nfc_tap(payload: NfcTapPayload):
    """Optional NFC reader webhook. Does not invent taps — only records POSTed events."""
    try:
        tap = record_tap(
            payload.product_id,
            zone=payload.zone,
            zone_id=payload.zone_id,
            camera_id=payload.camera_id,
            tapped_at=payload.tapped_at,
            meta=payload.meta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "ok": True,
        "tap": tap,
        "nfc": nfc_live_block(20),
    }


@app.get("/api/v1/nfc/taps")
def get_nfc_taps(limit: int = 20):
    """Recent NFC taps this session (empty until a reader POSTs)."""
    return nfc_live_block(limit)


@app.get("/api/v1/live/snapshot")
def get_live_snapshot(camera_id: Optional[str] = None):
    """Raw frame-synced live JSON (YOLO overlay companion)."""
    snap = _read_live_snapshot(camera_id)
    if not snap:
        raise HTTPException(
            status_code=404,
            detail="No live snapshot yet — is edge-analyzer processing video?",
        )
    nfc = nfc_live_block(20)
    out = dict(snap)
    out["nfc"] = nfc
    out["retail_roles"] = retail_roles_block(snap, nfc)
    out["industry"] = industry_status_block(snap, nfc)  # deprecated
    if out.get("journey") is None:
        out["journey"] = build_journey_block(zones_from_snapshot_rows([snap]))
    return out



def _load_alerts_catalog_file() -> Dict[str, Any]:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    for p in (
        os.path.join(here, "alerts_catalog.json"),
        os.path.join(root, "docs", "handoff", "alerts-catalog-retail-grocery.json"),
    ):
        if os.path.isfile(p):
            with open(p, "r") as f:
                return json.load(f)
    return {"alerts": []}


@app.get("/api/v1/alerts")
def get_alerts(store_id: str = "store_mumbai_001", camera_id: Optional[str] = None):
    snap = _read_live_snapshot(camera_id)
    if snap and snap.get("alerts"):
        out = dict(snap["alerts"])
        out["store_id"] = store_id
        out["camera_id"] = camera_id or snap.get("camera_id")
        out["source"] = "live_snapshot"
        return out
    catalog = _load_alerts_catalog_file()
    partial, future = [], []
    for rule in catalog.get("alerts") or []:
        status = (rule.get("data_status") or "FUTURE").upper()
        row = {
            "id": rule.get("id"),
            "title": rule.get("title"),
            "data_status": status,
            "recommended_action": rule.get("recommended_action"),
        }
        if status == "PARTIAL":
            row["chip"] = "pending calibration/upgrade"
            partial.append(row)
        elif status == "FUTURE":
            row["chip"] = "requires external data source"
            future.append(row)
    return {
        "store_id": store_id,
        "camera_id": camera_id,
        "active": [],
        "partial_catalog": partial,
        "future_catalog": future,
        "catalog_version": catalog.get("version") or catalog.get("catalog"),
        "source": "catalog_only",
        "note": "No live snapshot alerts yet — active list empty (not invented).",
    }


@app.get("/api/v1/analytics/floor")
def get_floor_analytics(window_seconds: int = 900, camera_id: Optional[str] = None):
    snap = _read_live_snapshot(camera_id)
    if not snap:
        raise HTTPException(status_code=404, detail="No live snapshot yet")
    floor = snap.get("floor")
    if floor is None:
        return {
            "store_id": snap.get("store_id"),
            "camera_id": snap.get("camera_id"),
            "window_seconds": window_seconds,
            "top_routes": [],
            "zone_traction": [],
            "paths_active": [],
            "status": "PARTIAL",
            "badge_copy": "Floor paths unlock after edge snapshot carries floor block.",
            "coverage_note": "session-cam only; no cross-day identity",
        }
    out = dict(floor)
    out["store_id"] = snap.get("store_id")
    out["camera_id"] = snap.get("camera_id")
    out["requested_window_seconds"] = window_seconds
    return out


@app.get("/api/v1/live.queue")
def get_live_queue(store_id: str = "store_mumbai_001", camera_id: Optional[str] = None):
    """Per-queue now + KPI window (contract: docs/handoff/queue-analytics-upgrade.md).

    Reads frame-synced snapshot rows; KPI fields stay null/empty while the window is
    under-sampled — the honest empty state from the alert catalog.
    """
    live_dir = _live_dir()
    queues = []
    if os.path.isdir(live_dir):
        for name in sorted(os.listdir(live_dir)):
            if not name.endswith(".json") or name in ("store.json",) or name.endswith(".tmp.json"):
                continue
            try:
                with open(os.path.join(live_dir, name)) as f:
                    row = json.load(f)
            except Exception:
                continue
            if camera_id and row.get("camera_id") != camera_id:
                continue
            vl = row.get("video_loop") or {}
            for q in row.get("queues") or []:
                queues.append({
                    "queue_id": q.get("id", "queue"),
                    "name": q.get("name"),
                    "camera_id": row.get("camera_id"),
                    "now": q.get("now") or {"length": q.get("queue_length", 0)},
                    "kpi": q.get("kpi") or {},
                    "series": q.get("series") or [],
                    "recent_episodes": q.get("recent_episodes") or [],
                    "abandon_status": q.get("abandon_status", "PARTIAL"),
                    "abandon_note": q.get("abandon_note"),
                    "staff_zone_id": q.get("staff_zone_id"),
                    "loop_count": vl.get("loop_count"),
                    "is_simulated": vl.get("is_simulated"),
                })
    return {
        "store_id": store_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "queues": queues,
    }


@app.get("/api/v1/live.staff")
def get_live_staff(store_id: str = "store_mumbai_001", camera_id: Optional[str] = None):
    """Per-approach staff presence from geometry-based dwell tagging (no facial ID)."""
    live_dir = _live_dir()
    zones = []
    queue_response = []
    response_times = []
    note = (
        "Geometry-based sticky staff tag; no facial ID. "
        "response_time_to_queue null until queue alert/join pairs with a linked staff zone."
    )
    if os.path.isdir(live_dir):
        for name in sorted(os.listdir(live_dir)):
            if not name.endswith(".json") or name in ("store.json",) or name.endswith(".tmp.json"):
                continue
            try:
                with open(os.path.join(live_dir, name)) as f:
                    row = json.load(f)
            except Exception:
                continue
            if camera_id and row.get("camera_id") != camera_id:
                continue
            for z in row.get("staff_zones") or []:
                zones.append({**z, "camera_id": z.get("camera_id") or row.get("camera_id")})
            staff = row.get("staff") or {}
            if isinstance(staff, dict):
                queue_response.extend(staff.get("queue_response") or [])
                rt = staff.get("response_time_to_queue")
                if rt is not None:
                    response_times.append(float(rt))
                if staff.get("note"):
                    note = staff["note"]
    present = sum(int(z.get("tagged_ids", 0) or 0) for z in zones)
    median = None
    if response_times:
        ordered = sorted(response_times)
        mid = len(ordered) // 2
        median = ordered[mid] if len(ordered) % 2 else round((ordered[mid - 1] + ordered[mid]) / 2.0, 1)
    return {
        "store_id": store_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "zones": zones,
        "camera_inventory_present": present,
        "queue_response": queue_response[-20:],
        "response_time_to_queue": median,
        "note": note,
    }


class DeviceRegister(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    inference_engine: Optional[str] = None
    perf_mode: Optional[str] = None
    cameras: Optional[int] = None
    python_version: Optional[str] = None
    torch_version: Optional[str] = None


@app.post("/api/v1/device/register")
def device_register(body: DeviceRegister):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO device_registry (
            device_id, device_name, inference_engine, perf_mode, cameras,
            python_version, torch_version, registered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
            device_name = excluded.device_name,
            inference_engine = excluded.inference_engine,
            perf_mode = excluded.perf_mode,
            cameras = excluded.cameras,
            python_version = excluded.python_version,
            torch_version = excluded.torch_version,
            registered_at = excluded.registered_at
        """, (
            body.device_id, body.device_name, body.inference_engine, body.perf_mode,
            body.cameras, body.python_version, body.torch_version,
            time.strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()
    return {"status": "success", "device_id": body.device_id}


# Metric Reset Endpoint (Clears accumulated test telemetry)
@app.post("/api/v1/metrics/reset")
def reset_metrics():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM telemetry_rollups")
        conn.execute("DELETE FROM telemetry_events")
        conn.commit()
    return {"status": "success", "message": "Telemetry database reset successfully."}

# Historical Rollup Series for Charts
@app.get("/api/v1/history")
def get_history(
    store_id: str = "store_mumbai_001",
    camera_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50
):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM telemetry_rollups WHERE store_id = ?"
        params: List[Any] = [store_id]
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        if start_date:
            query += " AND date(received_at) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(received_at) <= date(?)"
            params.append(end_date)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in reversed(rows)]

# Peak/Average Traffic Analytics Summary
@app.get("/api/v1/analytics/summary")
def get_analytics_summary(
    store_id: str = "store_mumbai_001",
    camera_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = """
        SELECT strftime('%Y-%m-%d %H:00:00', received_at) AS hour_bucket,
               SUM(in_count) AS visitors,
               SUM(out_count) AS exits
        FROM telemetry_rollups
        WHERE store_id = ?
        """
        params: List[Any] = [store_id]
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        if start_date:
            query += " AND date(received_at) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(received_at) <= date(?)"
            params.append(end_date)
        query += " GROUP BY hour_bucket ORDER BY hour_bucket ASC"
        rows = conn.execute(query, params).fetchall()

        hourly = [
            {"hour": r["hour_bucket"], "visitors": r["visitors"] or 0, "exits": r["exits"] or 0}
            for r in rows
        ]
        if hourly:
            peak = max(hourly, key=lambda h: h["visitors"])
            avg_visitors_per_hour = round(sum(h["visitors"] for h in hourly) / len(hourly), 1)
        else:
            peak = None
            avg_visitors_per_hour = 0.0

        return {
            "store_id": store_id,
            "camera_id": camera_id,
            "start_date": start_date,
            "end_date": end_date,
            "peak_period": peak,
            "avg_visitors_per_hour": avg_visitors_per_hour,
            "total_visitors": sum(h["visitors"] for h in hourly),
            "total_exits": sum(h["exits"] for h in hourly),
            "hourly_breakdown": hourly
        }

# --- Enrichment analytics -------------------------------------------------------
# Engagement, social grouping, population cohorts and product interest. These come
# from the edge node's slow tier and are synced alongside the traffic rollups.

@app.get("/api/v1/analytics/engagement")
def get_engagement_analytics(
    store_id: str = "store_mumbai_001",
    camera_id: Optional[str] = None,
    limit: int = 50
):
    """Attention, facing and phone-use rates over time."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = """
        SELECT camera_id, timestamp_start, timestamp_end,
               avg_attention_score, facing_ratio, phone_usage_rate, engaged_ratio,
               group_count, people_in_groups, demographics_json
        FROM telemetry_rollups
        WHERE store_id = ? AND avg_attention_score IS NOT NULL
        """
        params: List[Any] = [store_id]
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()

        series = []
        for r in reversed(rows):
            series.append({
                "camera_id": r["camera_id"],
                "timestamp_start": r["timestamp_start"],
                "timestamp_end": r["timestamp_end"],
                "avg_attention_score": r["avg_attention_score"],
                "facing_ratio": r["facing_ratio"],
                "phone_usage_rate": r["phone_usage_rate"],
                "engaged_ratio": r["engaged_ratio"],
                "group_count": r["group_count"],
                "people_in_groups": r["people_in_groups"],
            })

        def _avg(field):
            vals = [s[field] for s in series if s[field] is not None]
            return round(sum(vals) / len(vals), 3) if vals else None

        return {
            "store_id": store_id,
            "camera_id": camera_id,
            "windows": len(series),
            "avg_attention_score": _avg("avg_attention_score"),
            "avg_facing_ratio": _avg("facing_ratio"),
            "avg_phone_usage_rate": _avg("phone_usage_rate"),
            "avg_engaged_ratio": _avg("engaged_ratio"),
            "avg_group_count": _avg("group_count"),
            "series": series,
        }

@app.get("/api/v1/models/stack")
def get_model_stack():
    """Honest model-stack catalog (LIVE|PACKED|PARTIAL|GATED|FUTURE|SKIP).

    Never invents LIVE age/gender. See docs/model-stack-policy.md.
    """
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if root not in sys.path:
            sys.path.insert(0, root)
        from src.perception.model_stack import build_model_stack
        return build_model_stack(root)
    except Exception as e:
        logger.exception("model stack catalog failed")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "policy": "docs/model-stack-policy.md"},
        )


@app.get("/api/v1/analytics/demographics")
def get_demographics_analytics(
    store_id: str = "store_mumbai_001",
    camera_id: Optional[str] = None
):
    """The latest k-anonymous population cohorts for the store.

    The edge node only sends cohorts that already cleared the k-anonymity
    threshold, so everything in this response describes at least k individuals.
    Gated by ENABLE_DEMOGRAPHICS (default 0) — returns EMPTY when off.
    """
    if os.environ.get("ENABLE_DEMOGRAPHICS", "0").strip().lower() not in (
        "1", "true", "yes", "on",
    ):
        return {
            "store_id": store_id,
            "camera_id": camera_id,
            "available": False,
            "status": "GATED",
            "reason": (
                "ENABLE_DEMOGRAPHICS=0 (default). "
                "Demographics stay EMPTY/FUTURE until DPIA + k≥10 gate is wired."
            ),
            "demographics": None,
        }
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = """
        SELECT camera_id, timestamp_start, timestamp_end, demographics_json
        FROM telemetry_rollups
        WHERE store_id = ? AND demographics_json IS NOT NULL AND demographics_json != ''
        """
        params: List[Any] = [store_id]
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        query += " ORDER BY id DESC LIMIT 1"
        row = conn.execute(query, params).fetchone()

    if row is None:
        return {
            "store_id": store_id,
            "camera_id": camera_id,
            "available": False,
            "reason": "no k-anonymous cohorts have been synced yet",
            "demographics": None,
        }

    try:
        payload = json.loads(row["demographics_json"])
    except (TypeError, ValueError):
        payload = None

    return {
        "store_id": store_id,
        "camera_id": row["camera_id"],
        "available": payload is not None,
        "timestamp_start": row["timestamp_start"],
        "timestamp_end": row["timestamp_end"],
        "demographics": payload,
    }

@app.get("/api/v1/analytics/products")
def get_product_analytics(
    store_id: str = "store_mumbai_001",
    camera_id: Optional[str] = None,
    hours: int = 24,
    limit: int = 100
):
    """Per-category product interest: viewers, detections and dwell time."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = """
        SELECT category,
               SUM(viewers) AS viewers,
               SUM(detections) AS detections,
               SUM(total_dwell_seconds) AS total_dwell_seconds,
               COUNT(*) AS windows
        FROM telemetry_products
        WHERE store_id = ?
          AND datetime(received_at) >= datetime('now', ?)
        """
        params: List[Any] = [store_id, f"-{int(hours)} hours"]
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        query += " GROUP BY category ORDER BY total_dwell_seconds DESC, viewers DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()

        categories = []
        for r in rows:
            windows = r["windows"] or 0
            total_dwell = r["total_dwell_seconds"] or 0.0
            categories.append({
                "category": r["category"],
                "viewers": r["viewers"] or 0,
                "detections": r["detections"] or 0,
                "total_dwell_seconds": round(total_dwell, 1),
                "avg_dwell_seconds": round(total_dwell / windows, 1) if windows else 0.0,
                "windows": windows,
            })

        return {
            "store_id": store_id,
            "camera_id": camera_id,
            "hours": hours,
            "categories": categories,
        }

# Camera Discovery Endpoint
@app.get("/api/v1/cameras")
def list_cameras():
    frames_dir = os.path.join(os.path.dirname(DB_PATH), "frames")
    cams = []
    if os.path.exists(frames_dir):
        for f in os.listdir(frames_dir):
            if f.endswith(".jpg") and not f.endswith(".tmp.jpg"):
                cams.append(f.replace(".jpg", ""))
    if not cams:
        # Fallback to configured cameras in yaml
        cams = [c.get("id") for c in get_camera_configs().get("cameras", []) if c.get("id")]
    return {"cameras": cams or ["cam_entrance_01"]}

# Camera Frame Snapshot
@app.get("/api/v1/snapshot/{camera_id}")
def get_snapshot(camera_id: str):
    frames_dir = os.path.join(os.path.dirname(DB_PATH), "frames")
    frame_path = os.path.join(frames_dir, f"{camera_id}.jpg")
    if not os.path.exists(frame_path):
        raise HTTPException(status_code=404, detail=f"No frame found for camera {camera_id}")
    with open(frame_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# Live Fluid Video Stream (MJPEG)

@app.get("/api/v1/heatmap/{camera_id}")
def get_heatmap(camera_id: str):
    path = os.path.join(os.path.dirname(DB_PATH), "heatmaps", f"{camera_id}.jpg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No heatmap yet for camera {camera_id}")
    with open(path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/api/v1/stream/{camera_id}")
def get_stream(camera_id: str):
    frames_dir = os.path.join(os.path.dirname(DB_PATH), "frames")
    frame_path = os.path.join(frames_dir, f"{camera_id}.jpg")

    def frame_generator():
        # Edge writes via tmp + os.replace; still skip incomplete/torn JPEGs and
        # avoid re-yielding the same payload every tick (reduces MJPEG glitches).
        last_bytes: Optional[bytes] = None
        while True:
            if os.path.exists(frame_path):
                try:
                    with open(frame_path, "rb") as f:
                        frame_bytes = f.read()
                    # Valid JPEG: SOI … EOI; reject partial annotates mid-write races.
                    if (
                        len(frame_bytes) >= 100
                        and frame_bytes[:2] == b"\xff\xd8"
                        and frame_bytes[-2:] == b"\xff\xd9"
                        and frame_bytes != last_bytes
                    ):
                        last_bytes = frame_bytes
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                        )
                except Exception:
                    pass
            time.sleep(0.08)  # ~12 FPS streaming rate

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

# Dynamic Camera Configuration (Hot Reloadable Calibration API)
@app.get("/api/v1/config/cameras")
def get_camera_configs():
    if not os.path.exists(CONFIG_PATH) or yaml is None:
        return {"cameras": []}
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f) or {"cameras": []}
    config["cameras"] = [_redact_camera(c) for c in config.get("cameras", [])]
    return config

@app.post("/api/v1/config/cameras")
def update_camera_configs(config: Dict[str, Any] = Body(...)):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            if yaml:
                yaml.safe_dump(config, f, sort_keys=False)
            else:
                json.dump(config, f)
        logger.info("Successfully updated cameras configuration on disk.")
        return {"status": "success", "message": "Camera configuration updated and applied successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write configuration: {e}")

def _read_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH) or yaml is None:
        return {"cameras": []}
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {"cameras": []}

def _write_config(config: Dict[str, Any]):
    if yaml is None:
        raise HTTPException(status_code=500, detail="PyYAML is required to edit camera configuration")
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)
    os.replace(tmp_path, CONFIG_PATH)  # atomic, so the edge never reads a half-written file

def _find_camera(config: Dict[str, Any], camera_id: str) -> Dict[str, Any]:
    for cam in config.get("cameras", []):
        if cam.get("id") == camera_id:
            return cam
    raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' is not configured")

def _validate_source(source: str) -> str:
    source = (source or "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="Source must not be empty")
    if source.lower().startswith(STREAM_PREFIXES):
        return source
    normalized = os.path.normpath(source).replace("\\", "/")
    video_dir = os.path.normpath(VIDEO_DIR).replace("\\", "/")
    if not normalized.startswith(video_dir + "/"):
        raise HTTPException(status_code=400, detail=f"Local sources must live under {VIDEO_DIR}/ (or use an rtsp:// URL)")
    if not normalized.lower().endswith(VIDEO_EXTS):
        raise HTTPException(status_code=400, detail=f"Unsupported video type; expected one of {', '.join(VIDEO_EXTS)}")
    if not os.path.isfile(normalized):
        raise HTTPException(status_code=400, detail=f"Video file not found: {normalized}")
    return normalized

class SourceUpdate(BaseModel):
    source: str
    name: Optional[str] = None
    fps_target: Optional[int] = Field(default=None, ge=1, le=60)

class TripwireConfig(BaseModel):
    id: str
    name: Optional[str] = None
    line: List[List[float]]
    in_direction: str = "top_to_bottom"

    @field_validator("line")
    @classmethod
    def _two_points(cls, v):
        if len(v) != 2 or any(len(p) != 2 for p in v):
            raise ValueError("line must be exactly two [x, y] points")
        return v

    @field_validator("in_direction")
    @classmethod
    def _direction(cls, v):
        if v not in ("top_to_bottom", "bottom_to_top"):
            raise ValueError("in_direction must be 'top_to_bottom' or 'bottom_to_top'")
        return v

_ZONE_TYPES = (
    "dwell", "queue", "staff", "glass",
    "exit_corridor", "restricted", "aisle",
)

class ZoneConfig(BaseModel):
    id: str
    name: Optional[str] = None
    polygon: List[List[float]]
    # Shared physical store-zone key; only an identical key across cameras is eligible for fusion.
    store_zone_id: Optional[str] = None
    type: str = "dwell"
    max_comfortable_queue: Optional[int] = Field(default=None, ge=1)
    congestion_threshold_seconds: Optional[float] = Field(default=None, gt=0)
    service_point: Optional[List[float]] = None
    service_radius_frac: Optional[float] = None
    alert_wait_ms: Optional[int] = None
    alert_length: Optional[int] = None
    staff_zone_id: Optional[str] = None
    expected_on_post: Optional[int] = None
    linked_queue_ids: Optional[List[str]] = None
    min_stop_seconds: Optional[float] = None
    zone_capacity_people: Optional[int] = None
    blocked_grace_seconds: Optional[float] = None
    entry_grace_seconds: Optional[float] = None

    @field_validator("polygon")
    @classmethod
    def _polygon(cls, v):
        if len(v) < 3 or any(len(p) != 2 for p in v):
            raise ValueError("polygon needs at least three [x, y] points")
        return v

    @field_validator("type")
    @classmethod
    def _type(cls, v):
        if v not in _ZONE_TYPES:
            raise ValueError(f"zone type must be one of {list(_ZONE_TYPES)}")
        return v

class GlassViewConfig(BaseModel):
    id: str
    name: Optional[str] = None
    polygon: List[List[float]]
    min_stop_seconds: Optional[float] = Field(default=5.0, ge=2.0, le=60.0)

    @field_validator("polygon")
    @classmethod
    def _polygon(cls, v):
        if len(v) < 3 or any(len(p) != 2 for p in v):
            raise ValueError("glass polygon needs at least three [x, y] points")
        return v

class CalibrationUpdate(BaseModel):
    tripwires: Optional[List[TripwireConfig]] = None
    zones: Optional[List[ZoneConfig]] = None
    glass_views: Optional[List[GlassViewConfig]] = None
    # 3x3 image-pixel → shared store-floor coordinates, measured during calibration.
    floor_homography: Optional[List[List[float]]] = None

    @field_validator("floor_homography")
    @classmethod
    def _floor_homography(cls, v):
        if v is None:
            return v
        if len(v) != 3 or any(len(row) != 3 for row in v):
            raise ValueError("floor_homography must be a 3x3 matrix")
        try:
            for row in v:
                for value in row:
                    float(value)
        except (TypeError, ValueError):
            raise ValueError("floor_homography entries must be numeric")
        return v

# Selectable video files for the camera source switcher
@app.get("/api/v1/config/sources")
def list_video_sources():
    if not os.path.isdir(VIDEO_DIR):
        return {"video_dir": VIDEO_DIR, "videos": []}
    videos = sorted(f for f in os.listdir(VIDEO_DIR) if f.lower().endswith(VIDEO_EXTS))
    return {"video_dir": VIDEO_DIR, "videos": [f"{VIDEO_DIR}/{f}" for f in videos]}

# Switch one camera's input source without touching its calibration or other cameras
@app.post("/api/v1/config/cameras/{camera_id}/source")
def update_camera_source(camera_id: str, body: SourceUpdate):
    source = _validate_source(body.source)
    config = _read_config()
    cam = _find_camera(config, camera_id)
    cam["source"] = source
    if body.name:
        cam["name"] = body.name
    if body.fps_target:
        cam["fps_target"] = body.fps_target
    _write_config(config)
    logger.info(f"Camera {camera_id} source set to {_redact_source(source)}")
    return {"status": "success", "camera": _redact_camera(cam)}

# Replace one camera's tripwires/zones, leaving everything else in the file intact
@app.post("/api/v1/config/cameras/{camera_id}/calibration")
def update_camera_calibration(camera_id: str, body: CalibrationUpdate):
    config = _read_config()
    cam = _find_camera(config, camera_id)
    if body.tripwires is not None:
        cam["tripwires"] = [t.model_dump(exclude_none=True) for t in body.tripwires]
    if body.zones is not None:
        cam["zones"] = [z.model_dump(exclude_none=True) for z in body.zones]
    if body.glass_views is not None:
        cam["glass_views"] = [g.model_dump(exclude_none=True) for g in body.glass_views]
    if body.floor_homography is not None:
        cam["floor_homography"] = body.floor_homography
    _write_config(config)
    return {"status": "success", "camera": _redact_camera(cam)}

_OVERLAY_STYLES = frozenset({"foot", "skeleton", "nvidia", "parallel", "aabb"})
_OVERLAY_ALIASES = {"pallet": "nvidia"}


def _resolve_overlay_box_style(snap: Optional[Dict[str, Any]] = None) -> str:
    """Read overlay style from live snapshot (edge) or local env; default foot."""
    if snap:
        style = snap.get("overlay_box_style") or (snap.get("models") or {}).get("overlay_box_style")
        if style:
            style = _OVERLAY_ALIASES.get(str(style).lower(), str(style).lower())
            if style in _OVERLAY_STYLES:
                return style
    raw = (os.environ.get("OVERLAY_BOX_STYLE") or "foot").strip().lower()
    raw = _OVERLAY_ALIASES.get(raw, raw)
    return raw if raw in _OVERLAY_STYLES else "foot"


@app.get("/api/v1/overlay")
def get_overlay_settings():
    """Visual overlay flags only (no KPIs). Edge applies OVERLAY_BOX_STYLE on annotated MJPEG."""
    snap = _read_live_snapshot()
    style = _resolve_overlay_box_style(snap)
    return {
        "overlay_box_style": style,
        "options": ["foot", "skeleton", "nvidia", "parallel", "aabb"],
        "default": "foot",
        "note": (
            "Set OVERLAY_BOX_STYLE=foot|skeleton|nvidia|parallel|aabb on edge-analyzer (Compose) "
            "and restart. Default foot = one red ground mark (tripwire/dwell use that point). "
            "skeleton adds bones on the foot. nvidia/parallel/aabb are opt-in and do not also "
            "draw the foot (stacked marks shimmered). LocateAnything-3B is not downloaded."
        ),
        "docs": "docs/cv-pipeline-unified.md",
    }


# Device Hardware Health Endpoint
@app.get("/api/v1/device/health")
def get_device_health():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
    except ImportError:
        cpu = 14.2
        mem = 38.5
    # clock_sync.ntp_ok stays null until chrony/systemd-timesyncd is verified on the host.
    # Frame stamps use host wall + monotonic; do not treat association windows as NTP-safe yet.
    snap = _read_live_snapshot()
    # Never invent FPS — null until a live snapshot exists.
    pipeline_fps = None
    if snap and snap.get("infer_fps") is not None:
        pipeline_fps = float(snap.get("infer_fps") or 0)
    elif snap and snap.get("decode_fps") is not None:
        pipeline_fps = float(snap.get("decode_fps") or 0)
    models = (snap or {}).get("models") or {}
    perf_mode = (
        (snap or {}).get("perf_mode")
        or models.get("perf_mode")
        or os.environ.get("EDGE_PERF_MODE")
        or "fast"
    )
    # Honest engine label: Compose edge is CPU; do not claim Core ML inside Docker.
    with sqlite3.connect(DB_PATH) as _conn:
        _reg = _conn.execute(
            "SELECT device_name, inference_engine, device_id FROM device_registry "
            "ORDER BY registered_at DESC LIMIT 1"
        ).fetchone()
    if _reg and _reg[1]:
        engine = _reg[1]
    else:
        # Honest fallback until the edge self-registers (POST /api/v1/device/register).
        engine = "PyTorch CPU (Docker)" if os.path.exists("/.dockerenv") else "PyTorch MPS (native; self-registration pending)"
    return {
        "device_id": "edge_node_macmini_01",
        "device_name": "Apple Silicon Mac mini (Edge Node)",
        "cpu_usage_percent": cpu,
        "memory_usage_percent": mem,
        "inference_engine": engine,
        "pipeline_fps": pipeline_fps,
        "decode_fps": snap.get("decode_fps") if snap else None,
        "infer_fps": snap.get("infer_fps") if snap else None,
        "people_now": snap.get("people_now") if snap else None,
        "perf_mode": perf_mode,
        "overlay_box_style": _resolve_overlay_box_style(snap),
        "person_detector": models.get("person_detector") or models.get("detect_model"),
        "status": "Healthy (Online)",
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "live_source": "live_snapshot" if snap and not snap.get("_stale") else "none",
        "clock_sync": {
            "ntp_ok": None,
            "max_estimated_skew_ms": None,
            "note": "Host NTP not probed yet. Frames carry capture_ts_utc (wall) + capture_ts_mono.",
        },
        "reid": {
            "cross_cam_fusion": False,
            "session_scoped": True,
            "active": bool((snap or {}).get("reid", {}).get("active")) if snap else None,
            "backend": (snap or {}).get("reid", {}).get("backend") if snap else None,
            "gallery_size": (snap or {}).get("reid", {}).get("gallery_size") if snap else None,
            "flag": (
                "models.reid.enabled: true + EDGE_PERF_MODE=quality "
                "(ONNX OSNet/YouTu; session-scoped). Fast mode keeps ReID off for FPS."
            ),
            "note": (
                "Soft body ReID only — no face ID / multi-day gallery. "
                "Fusion / global_person_id is Future."
            ),
        },
    }
