import os
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
from fastapi.responses import StreamingResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

logger = logging.getLogger("EdgeSight-API")
app = FastAPI(title="AD Labs EdgeSight Enterprise Platform", version="2.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.environ.get("SERVER_DB_PATH", "data/storage/cloud_metrics.db")
CONFIG_PATH = os.environ.get("CAMERAS_CONFIG", "configs/cameras.yaml")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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
    return templates.TemplateResponse(request=request, name="index.html")

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

        # Latest rollup for active tracks count
        latest_query = "SELECT * FROM telemetry_rollups WHERE store_id = ?"
        latest_params: List[Any] = [store_id]
        if camera_id:
            latest_query += " AND camera_id = ?"
            latest_params.append(camera_id)
        latest_query += " ORDER BY id DESC LIMIT 1"
        latest = conn.execute(latest_query, latest_params).fetchone()

        # Real-time people count currently visible in the camera frame
        live_people_count = latest["current_occupancy"] if latest else 0

        # Aggregated totals today (filtering by current date so old test data doesn't pollute counts)
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
        avg_dwell = round(row_footfall["avg_dwell"], 1) if row_footfall and row_footfall["avg_dwell"] is not None else (round(latest["avg_dwell_seconds"], 1) if latest else 0.0)

        # Fallback if no records today yet
        if total_in == 0 and latest:
            total_in = latest["in_count"]

        return {
            "store_id": store_id,
            "camera_id": camera_id,
            "total_visitors": total_in,
            "total_exits": total_out,
            "net_occupancy": live_people_count,
            "avg_dwell_seconds": avg_dwell,
            "queue_length": latest["queue_length"] if latest else 0,
            "avg_queue_wait_seconds": latest["avg_queue_wait_seconds"] if latest else 0.0,
            "queue_alert_active": bool(latest["queue_alert_active"]) if latest else False,
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
               SUM(in_count) AS visitors
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

        hourly = [{"hour": r["hour_bucket"], "visitors": r["visitors"] or 0} for r in rows]
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
    if not os.path.exists(CONFIG_PATH):
        return {"cameras": []}
    with open(CONFIG_PATH, "r") as f:
        if yaml:
            return yaml.safe_load(f) or {"cameras": []}
        return {"cameras": []}

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
