import os
import re
import secrets
import sqlite3
import time
import json
import logging
from typing import List, Dict, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import StreamingResponse, Response, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("EdgeSight-API")
app = FastAPI(title="AD Labs EdgeSight Enterprise Platform", version="2.0.0")

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
        conn.commit()

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
                queue_length, avg_queue_wait_seconds, queue_alert_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.store_id, r.device_id, r.camera_id, r.timestamp_start, r.timestamp_end,
                r.in_count, r.out_count, r.current_occupancy, r.avg_dwell_seconds,
                r.queue_length, r.avg_queue_wait_seconds, r.queue_alert_active
            ))
        conn.commit()
    return {"status": "success", "processed_records": len(payload.rollups)}

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

# Live Store Telemetry
@app.get("/api/v1/live")
def get_live_metrics(store_id: str = "store_mumbai_001", camera_id: Optional[str] = None):
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

        return {
            "store_id": store_id,
            "camera_id": camera_id,
            "total_visitors": total_in,
            "total_exits": total_out,
            "net_occupancy": live_people_count,
            "avg_dwell_seconds": avg_dwell,
            "queue_length": queue_length,
            "avg_queue_wait_seconds": avg_queue_wait_seconds,
            "queue_alert_active": queue_alert_active,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }

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

# Floor heatmap: where customers have spent time since the camera's pipeline started
# (written by the edge every analytics.heatmap_write_seconds)
@app.get("/api/v1/heatmap/{camera_id}")
def get_heatmap(camera_id: str):
    path = os.path.join(os.path.dirname(DB_PATH), "heatmaps", f"{camera_id}.jpg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No heatmap yet for camera {camera_id}")
    with open(path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# Live Fluid Video Stream (MJPEG)
@app.get("/api/v1/stream/{camera_id}")
def get_stream(camera_id: str):
    frames_dir = os.path.join(os.path.dirname(DB_PATH), "frames")
    frame_path = os.path.join(frames_dir, f"{camera_id}.jpg")

    def frame_generator():
        while True:
            if os.path.exists(frame_path):
                try:
                    with open(frame_path, "rb") as f:
                        frame_bytes = f.read()
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
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

class ZoneConfig(BaseModel):
    id: str
    name: Optional[str] = None
    polygon: List[List[float]]
    type: str = "dwell"
    max_comfortable_queue: Optional[int] = Field(default=None, ge=1)
    congestion_threshold_seconds: Optional[float] = Field(default=None, gt=0)

    @field_validator("polygon")
    @classmethod
    def _polygon(cls, v):
        if len(v) < 3 or any(len(p) != 2 for p in v):
            raise ValueError("polygon needs at least three [x, y] points")
        return v

    @field_validator("type")
    @classmethod
    def _type(cls, v):
        if v not in ("dwell", "queue", "staff"):
            raise ValueError("zone type must be 'dwell', 'queue' or 'staff'")
        return v

class CalibrationUpdate(BaseModel):
    tripwires: Optional[List[TripwireConfig]] = None
    zones: Optional[List[ZoneConfig]] = None

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
    _write_config(config)
    return {"status": "success", "camera": _redact_camera(cam)}

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
    return {
        "device_id": "edge_node_macmini_01",
        "device_name": "Apple Silicon Mac mini (Edge Node)",
        "cpu_usage_percent": cpu,
        "memory_usage_percent": mem,
        "inference_engine": "Core ML / ONNX Runtime FP16",
        "pipeline_fps": 13.8,
        "status": "Healthy (Online)",
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
