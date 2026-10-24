"""Model-free supervisor for explicitly requested EdgeSight processing sessions."""

from __future__ import annotations

import hmac
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml


logger = logging.getLogger("EdgeSight-Supervisor")
CONTROL_KEY_HEADER = "X-Control-Key"
MAX_REQUEST_BYTES = 16_384
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}


class ProcessingSupervisor:
    """Own one inference child and persist lifecycle status without loading CV code."""

    def __init__(
        self,
        camera_config_path: str,
        state_dir: str,
        control_key: str,
        pipeline_config_path: str = "configs/pipeline.yaml",
        *,
        popen_factory: Callable[..., Any] = subprocess.Popen,
        shutdown_timeout_seconds: float = 10.0,
    ) -> None:
        self.camera_config_path = camera_config_path
        self.pipeline_config_path = pipeline_config_path
        self.state_dir = Path(state_dir)
        self.live_state_path = self.state_dir / "live.json"
        self.control_key = control_key
        self.popen_factory = popen_factory
        self.shutdown_timeout_seconds = shutdown_timeout_seconds
        self._lock = threading.RLock()
        self._child: Any = None
        self._session_id: str | None = None
        self._camera_ids: list[str] = []
        self._state = "OFF"
        self._started_at: float | None = None
        self._updated_at = time.time()
        self._error: str | None = None
        # A supervisor restart must make the last worker's live snapshot stale
        # without clearing any aggregate counters or persisted rollups.
        try:
            self._mark_live_state("OFF", stale=True)
        except OSError as error:
            logger.warning("Could not mark prior live state stale: %s", error)

    def _configured_cameras(self) -> dict[str, dict[str, Any]]:
        with open(self.camera_config_path, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
        return {
            row["id"]: row
            for row in config.get("cameras", [])
            if isinstance(row, dict) and row.get("id") and row.get("enabled", True) is not False
        }

    def _validate_camera_ids(self, camera_ids: list[str]) -> list[str]:
        if not isinstance(camera_ids, list) or not camera_ids:
            raise ValueError("Select at least one configured camera before starting processing.")
        if any(not isinstance(camera_id, str) or not camera_id for camera_id in camera_ids):
            raise ValueError("Camera IDs must be non-empty strings.")
        if len(camera_ids) != len(set(camera_ids)):
            raise ValueError("Camera IDs must be unique.")
        configured = self._configured_cameras()
        unknown = [camera_id for camera_id in camera_ids if camera_id not in configured]
        if unknown:
            raise ValueError(f"Unknown or disabled camera ID(s): {', '.join(unknown)}")
        for camera_id in camera_ids:
            source = configured[camera_id].get("source")
            if not isinstance(source, str) or not source.strip():
                raise ValueError(f"Camera {camera_id} has no configured video source.")
            scheme = urlparse(source).scheme.lower()
            if scheme not in {"", "rtsp", "rtsps", "http"}:
                raise ValueError(f"Camera {camera_id} uses an unsupported source format.")
            if not scheme:
                source_path = Path(source)
                if not source_path.is_absolute():
                    source_path = Path.cwd() / source_path
                if not source_path.is_file():
                    raise ValueError(f"Configured video file for camera {camera_id} is missing.")
                if source_path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
                    raise ValueError(f"Camera {camera_id} uses an unsupported video file extension.")
        return camera_ids

    def _validate_required_detector_weights(self) -> None:
        """Fail before spawning when the configured mandatory person model is absent."""
        with open(self.pipeline_config_path, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
        perception = config.get("perception", {})
        if perception.get("require_model", False) is not True:
            return
        candidates = perception.get("model_name", [])
        if isinstance(candidates, str):
            candidates = [candidates]
        if not isinstance(candidates, list) or not candidates:
            raise ValueError("The required person detector has no configured weight path.")
        available = [str(path) for path in candidates if isinstance(path, str) and Path(path).is_file()]
        if not available:
            expected = ", ".join(str(path) for path in candidates if isinstance(path, str))
            raise ValueError(f"Required person detector weights are missing. Checked: {expected or '(no valid paths)' }.")

    def _worker_command(self, camera_ids: list[str]) -> tuple[list[str], dict[str, str]]:
        command = [sys.executable, "-m", "src.main", "--camera-ids", ",".join(camera_ids)]
        env = os.environ.copy()
        env["SUPERVISOR_URL"] = "http://127.0.0.1:8001"
        env["PROCESSING_CONTROL_KEY"] = self.control_key
        env["PROCESSING_SESSION_ID"] = self._session_id or ""
        return command, env

    def _refresh_child_state(self) -> None:
        if self._child is None:
            return
        return_code = self._child.poll()
        if return_code is not None and self._state not in {"OFF", "STOPPING", "ERROR"}:
            self._state = "ERROR"
            self._error = f"Inference worker exited before Stop (exit code {return_code})."
            self._updated_at = time.time()
            self._child = None
            self._mark_live_state("ERROR", stale=True)

    def status(self) -> dict[str, Any]:
        with self._lock:
            self._refresh_child_state()
            freshness: dict[str, bool] = {}
            try:
                live = json.loads(self.live_state_path.read_text(encoding="utf-8"))
                camera_rows = live.get("cameras", []) if isinstance(live, dict) else []
                by_id = {row.get("camera_id"): row for row in camera_rows if isinstance(row, dict)}
                now = time.time()
                for camera_id in self._camera_ids:
                    row = by_id.get(camera_id, {})
                    last_frame = row.get("last_frame_received_epoch")
                    freshness[camera_id] = (
                        row.get("session_id") == self._session_id
                        and isinstance(last_frame, (int, float))
                        and 0 <= now - last_frame <= 15.0
                    )
            except (OSError, ValueError, TypeError):
                freshness = {camera_id: False for camera_id in self._camera_ids}
            return {
                "state": self._state,
                "session_id": self._session_id,
                "camera_ids": list(self._camera_ids),
                "worker_pid": getattr(self._child, "pid", None),
                "started_at": self._started_at,
                "updated_at": self._updated_at,
                "error": self._error,
                "fresh": self._state == "RUNNING" and bool(freshness) and all(freshness.values()),
                "video_freshness": freshness,
            }

    def start(self, camera_ids: list[str]) -> dict[str, Any]:
        with self._lock:
            self._refresh_child_state()
            selected = self._validate_camera_ids(camera_ids)
            if self._state in {"STARTING", "RUNNING"}:
                if selected == self._camera_ids:
                    return self.status()
                raise RuntimeError("Processing is already active for a different camera selection.")
            self._validate_required_detector_weights()
            self._camera_ids = selected
            self._session_id = str(uuid.uuid4())
            self._started_at = time.time()
            self._updated_at = self._started_at
            self._error = None
            command, env = self._worker_command(selected)
            try:
                self._child = self.popen_factory(
                    command,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=None,
                    stderr=None,
                    close_fds=True,
                )
            except OSError as error:
                self._state = "ERROR"
                self._error = f"Could not start inference worker: {error}"
                self._child = None
                self._updated_at = time.time()
                self._mark_live_state("ERROR", stale=True)
                return self.status()
            self._state = "STARTING"
            self._updated_at = time.time()
            self._persist_status()
            logger.info("Started EdgeSight worker session %s for %s", self._session_id, selected)
            return self.status()

    def mark_ready(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            if not session_id or session_id != self._session_id or self._child is None:
                raise ValueError("Worker readiness does not match the active session.")
            self._refresh_child_state()
            if self._state == "ERROR":
                return self.status()
            self._state = "RUNNING"
            self._updated_at = time.time()
            self._persist_status()
            return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._refresh_child_state()
            if self._child is None:
                self._state = "OFF"
                self._updated_at = time.time()
                self._mark_live_state("OFF", stale=True)
                return self.status()
            child = self._child
            self._state = "STOPPING"
            self._updated_at = time.time()
            self._persist_status()
            child.terminate()
            forced = False
            try:
                child.wait(timeout=self.shutdown_timeout_seconds)
            except subprocess.TimeoutExpired:
                forced = True
                child.kill()
                try:
                    child.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._state = "ERROR"
                    self._error = "Worker did not exit after forced stop."
                    self._updated_at = time.time()
                    self._mark_live_state("ERROR", stale=True)
                    logger.error("EdgeSight worker session %s did not exit after kill", self._session_id)
                    return self.status()
            self._child = None
            self._state = "OFF"
            self._error = "Worker required a forced stop." if forced else None
            self._updated_at = time.time()
            self._mark_live_state("OFF", stale=True)
            logger.info("Stopped EdgeSight worker session %s", self._session_id)
            return self.status()

    def _persist_status(self) -> None:
        self._mark_live_state(self._state, stale=self._state != "RUNNING")

    def _mark_live_state(self, state: str, stale: bool) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            payload = json.loads(self.live_state_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            payload = {}
        # Preserve the most recent counts/rollups as historical context while making
        # their stale status explicit. No measurements are reset to zero on Stop.
        payload["processing"] = {
            "state": state,
            "stale": stale,
            "session_id": self._session_id,
            "camera_ids": list(self._camera_ids),
            "updated_at": time.time(),
        }
        tmp_path = self.live_state_path.with_suffix(".tmp.json")
        tmp_path.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp_path, self.live_state_path)


def make_handler(manager: ProcessingSupervisor, control_key: str):
    class Handler(BaseHTTPRequestHandler):
        def _authorized(self) -> bool:
            provided = self.headers.get(CONTROL_KEY_HEADER, "")
            return bool(control_key) and hmac.compare_digest(provided, control_key)

        def _send(self, status: int, body: dict[str, Any]) -> None:
            raw = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ValueError("Invalid content length.") from error
            if length < 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("Request body exceeds the allowed size.")
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError as error:
                raise ValueError("Request body must be valid JSON.") from error
            if not isinstance(body, dict):
                raise ValueError("Request body must be a JSON object.")
            return body

        def do_GET(self) -> None:  # noqa: N802
            if not self._authorized():
                self._send(401, {"detail": "Missing or invalid control key."})
            elif self.path != "/internal/processing/status":
                self._send(404, {"detail": "Not found."})
            else:
                self._send(200, manager.status())

        def do_POST(self) -> None:  # noqa: N802
            if not self._authorized():
                self._send(401, {"detail": "Missing or invalid control key."})
                return
            try:
                body = self._read_json()
                if self.path == "/internal/processing/start":
                    if set(body) != {"camera_ids"}:
                        raise ValueError("Start requires only a camera_ids array.")
                    self._send(202, manager.start(body["camera_ids"]))
                elif self.path == "/internal/processing/stop":
                    if body:
                        raise ValueError("Stop accepts an empty JSON object only.")
                    self._send(200, manager.stop())
                elif self.path == "/internal/processing/ready":
                    if set(body) != {"session_id"}:
                        raise ValueError("Ready requires only a session_id.")
                    self._send(200, manager.mark_ready(body["session_id"]))
                else:
                    self._send(404, {"detail": "Not found."})
            except RuntimeError as error:
                self._send(409, {"detail": str(error)})
            except (ValueError, TypeError) as error:
                self._send(400, {"detail": str(error)})

        def log_message(self, format_string: str, *args: Any) -> None:
            logger.info("supervisor %s - %s", self.address_string(), format_string % args)

    return Handler


def notify_worker_ready() -> None:
    """Tell the local supervisor that model loading and pipeline startup completed."""
    supervisor_url = os.environ.get("SUPERVISOR_URL")
    session_id = os.environ.get("PROCESSING_SESSION_ID")
    control_key = os.environ.get("PROCESSING_CONTROL_KEY")
    if not supervisor_url or not session_id or not control_key:
        return
    payload = json.dumps({"session_id": session_id}).encode("utf-8")
    request = Request(
        f"{supervisor_url.rstrip('/')}/internal/processing/ready",
        data=payload,
        headers={CONTROL_KEY_HEADER: control_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=3.0):
            pass
    except Exception as error:
        logger.error("Could not publish worker readiness to supervisor: %s", error)


def serve() -> None:
    control_key = os.environ.get("PROCESSING_CONTROL_KEY", "")
    if not control_key:
        raise RuntimeError("PROCESSING_CONTROL_KEY is required; supervisor remains stopped.")
    config_path = os.environ.get("CAMERAS_CONFIG", "configs/cameras.yaml")
    pipeline_config_path = os.environ.get("PIPELINE_CONFIG", "configs/pipeline.yaml")
    state_dir = os.environ.get("EDGE_STATE_DIR", "data/storage/state")
    manager = ProcessingSupervisor(config_path, state_dir, control_key, pipeline_config_path)
    host = os.environ.get("SUPERVISOR_HOST", "0.0.0.0")
    port = int(os.environ.get("SUPERVISOR_PORT", "8001"))
    server = ThreadingHTTPServer((host, port), make_handler(manager, control_key))
    server.daemon_threads = True
    logger.info("Model-free EdgeSight supervisor ready at %s:%s (processing OFF)", host, port)
    def request_shutdown(_signum: int, _frame: Any) -> None:
        # shutdown() must run outside the serve_forever thread.
        threading.Thread(target=server.shutdown, name="SupervisorShutdown", daemon=True).start()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        manager.stop()
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    serve()
