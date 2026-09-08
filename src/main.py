import os
import sys
import time
import signal
import yaml
import logging
from typing import Dict, List, Any

from src.ingestion.stream_reader import StreamReader
from src.perception.detector import PersonDetector
from src.perception.tracker import SimpleByteTracker
from src.analytics.tripwire import Tripwire
from src.analytics.zones import Zone
from src.analytics.queue_analyzer import QueueAnalyzer
from src.storage.local_buffer import LocalBuffer
from src.telemetry.exporter import TelemetryExporter
from src.telemetry.health import HealthMonitor
from src.visualizer.debug_overlay import DebugOverlay

try:
    import cv2
except ImportError:
    cv2 = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ADLabs-EdgeSight")

class EdgePipeline:
    def __init__(self, pipeline_config_path: str, cameras_config_path: str):
        self.pipeline_cfg = self._load_yaml(pipeline_config_path)
        self.cameras_cfg = self._load_yaml(cameras_config_path)

        self.store_id = self.pipeline_cfg.get("edge", {}).get("store_id", "store_default")
        self.device_id = self.pipeline_cfg.get("edge", {}).get("device_id", "edge_01")
        self.rollup_interval = self.pipeline_cfg.get("storage", {}).get("rollup_interval_seconds", 30)

        # Storage & Telemetry
        db_path = self.pipeline_cfg.get("storage", {}).get("db_path", "data/storage/edgesight.db")
        self.local_buffer = LocalBuffer(db_path=db_path)
        self.frames_dir = os.path.join(os.path.dirname(db_path), "frames")
        os.makedirs(self.frames_dir, exist_ok=True)

        cloud_endpoint = self.pipeline_cfg.get("telemetry", {}).get("cloud_endpoint", "http://localhost:8000/api/v1/telemetry")
        local_endpoint = self.pipeline_cfg.get("telemetry", {}).get("local_endpoint", "http://localhost:8000/api/v1/telemetry")
        self.exporter = TelemetryExporter(
            local_buffer=self.local_buffer,
            cloud_endpoint=cloud_endpoint,
            local_endpoint=local_endpoint,
            push_interval_seconds=self.pipeline_cfg.get("telemetry", {}).get("push_interval_seconds", 30)
        )
        self.health_monitor = HealthMonitor(self.device_id)

        # Perception model (shared across cameras to optimize memory)
        p_cfg = self.pipeline_cfg.get("perception", {})
        model_name = p_cfg.get("model_name", "yolov8n.pt")
        conf_thresh = p_cfg.get("confidence_threshold", 0.50)
        iou_thresh = p_cfg.get("iou_threshold", 0.45)
        min_height = p_cfg.get("min_height", 85.0)
        min_width = p_cfg.get("min_width", 30.0)
        min_aspect_ratio = p_cfg.get("min_aspect_ratio", 1.0)
        max_aspect_ratio = p_cfg.get("max_aspect_ratio", 4.2)
        min_area = p_cfg.get("min_area", 3000.0)

        self.detector = PersonDetector(
            model_name=model_name,
            conf_thresh=conf_thresh,
            iou_thresh=iou_thresh,
            min_height=min_height,
            min_width=min_width,
            min_aspect_ratio=min_aspect_ratio,
            max_aspect_ratio=max_aspect_ratio,
            min_area=min_area
        )

        self.cameras_cfg_path = cameras_config_path
        self.last_config_mtime = os.path.getmtime(cameras_config_path) if os.path.exists(cameras_config_path) else 0
        self.last_reload_check = time.time()

        # Camera context pipelines
        self.camera_contexts: Dict[str, Dict[str, Any]] = {}
        self._init_cameras()

        self.running = False

    def _load_yaml(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            logger.warning(f"Config file not found at {path}. Using defaults.")
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    def _init_cameras(self):
        cameras_list = self.cameras_cfg.get("cameras", [])
        t_cfg = self.pipeline_cfg.get("tracking", {})
        for cam in cameras_list:
            cam_id = cam["id"]
            cam_name = cam.get("name", cam_id)
            source = cam.get("source", "")
            fps_target = cam.get("fps_target", 15)

            reader = StreamReader(camera_id=cam_id, source=source, fps_target=fps_target)
            tracker = SimpleByteTracker(
                max_age=t_cfg.get("track_buffer", 30),
                iou_threshold=t_cfg.get("match_thresh", 0.45),
                min_hits=t_cfg.get("min_hits", 4),
                filter_stationary=t_cfg.get("filter_stationary", True)
            )

            tripwires = []
            for tw in cam.get("tripwires", []):
                tripwires.append(Tripwire(
                    wire_id=tw["id"],
                    name=tw.get("name", tw["id"]),
                    line=tw["line"],
                    in_direction=tw.get("in_direction", "top_to_bottom")
                ))

            zones = []
            queues = []
            for z in cam.get("zones", []):
                if z.get("type") == "queue":
                    queues.append(QueueAnalyzer(
                        zone_id=z["id"],
                        name=z.get("name", z["id"]),
                        polygon=z["polygon"],
                        max_comfortable_queue=z.get("max_comfortable_queue", 4),
                        congestion_threshold_seconds=z.get("congestion_threshold_seconds", 120.0)
                    ))
                else:
                    zones.append(Zone(
                        zone_id=z["id"],
                        name=z.get("name", z["id"]),
                        polygon=z["polygon"],
                        zone_type=z.get("type", "dwell")
                    ))

            self.camera_contexts[cam_id] = {
                "name": cam_name,
                "reader": reader,
                "tracker": tracker,
                "tripwires": tripwires,
                "zones": zones,
                "queues": queues,
                "tracked_ids_today": set(),
                "last_unique_count": 0,
                "current_active_tracks": [],
                "last_rollup_time": time.time(),
                "rollup_start_time": time.time(),
                "frames_processed": 0,
                "last_in_count": 0,
                "last_out_count": 0
            }
            logger.info(f"Initialized pipeline for camera: {cam_name} ({cam_id})")

    def start(self):
        self.running = True
        self.exporter.start()

        for ctx in self.camera_contexts.values():
            ctx["reader"].start()

        logger.info(f"AD Labs EdgeSight running for store '{self.store_id}'. Processing active streams...")

        try:
            while self.running:
                loop_start = time.time()
                for cam_id, ctx in self.camera_contexts.items():
                    item = ctx["reader"].get_latest_frame(timeout=0.01)
                    if item is None:
                        continue

                    frame_idx, frame_time, frame = item
                    ctx["frames_processed"] += 1

                    # 1. Perception
                    detections = self.detector.detect(frame)

                    # 2. Tracking
                    active_tracks = ctx["tracker"].update(detections, frame_time)
                    ctx["current_active_tracks"] = active_tracks
                    ctx["tracked_ids_today"].update(t.track_id for t in active_tracks)

                    # 3. Spatial Analytics
                    for tw in ctx["tripwires"]:
                        tw.update(active_tracks, frame_time)

                    for zone in ctx["zones"]:
                        zone.update(active_tracks, frame_time)

                    for q in ctx["queues"]:
                        q.update(active_tracks, frame_time)

                    # 4. Render and Save Live Vision Feed with Model Outputs (~8-10 FPS)
                    if cv2 is not None and ctx["frames_processed"] % 2 == 0:
                        try:
                            annotated = DebugOverlay.draw_pipeline(
                                frame=frame,
                                tracks=active_tracks,
                                tripwires=ctx["tripwires"],
                                zones=ctx["zones"],
                                queues=ctx["queues"],
                                camera_name=ctx["name"],
                                fps=ctx["reader"].fps_actual
                            )
                            frame_path = os.path.join(self.frames_dir, f"{cam_id}.jpg")
                            tmp_path = os.path.join(self.frames_dir, f"{cam_id}.tmp.jpg")
                            cv2.imwrite(tmp_path, annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                            os.replace(tmp_path, frame_path)
                        except Exception as e:
                            logger.debug(f"Frame export error for {cam_id}: {e}")

                    # 5. Check for Periodic Rollup Export
                    if frame_time - ctx["last_rollup_time"] >= self.rollup_interval:
                        self._generate_and_save_rollup(cam_id, ctx, frame_time)

                # 6. Check for dynamic configuration hot-reload every 3 seconds
                now = time.time()
                if now - self.last_reload_check >= 3.0:
                    self.check_hot_reload()
                    self.last_reload_check = now

                # Regulate loop to avoid 100% CPU busy-spin when no frames arrive
                elapsed = time.time() - loop_start
                if elapsed < 0.01:
                    time.sleep(0.01)

        except KeyboardInterrupt:
            logger.info("Shutdown requested by user.")
        finally:
            self.stop()

    def check_hot_reload(self):
        if not os.path.exists(self.cameras_cfg_path):
            return
        try:
            mtime = os.path.getmtime(self.cameras_cfg_path)
            if mtime > self.last_config_mtime:
                logger.info("Configuration file modified on disk. Hot-reloading cameras & tripwires...")
                self.last_config_mtime = mtime
                new_cfg = self._load_yaml(self.cameras_cfg_path)
                self._apply_camera_config_update(new_cfg)
        except Exception as e:
            logger.error(f"Error checking hot-reload: {e}")

    def _apply_camera_config_update(self, new_cfg: Dict[str, Any]):
        for cam in new_cfg.get("cameras", []):
            cam_id = cam["id"]
            if cam_id in self.camera_contexts:
                ctx = self.camera_contexts[cam_id]
                # Update Tripwires
                new_tripwires = []
                for tw in cam.get("tripwires", []):
                    new_tripwires.append(Tripwire(
                        wire_id=tw["id"],
                        name=tw.get("name", tw["id"]),
                        line=tw["line"],
                        in_direction=tw.get("in_direction", "top_to_bottom")
                    ))
                ctx["tripwires"] = new_tripwires

                # Update Zones & Queues
                new_zones = []
                new_queues = []
                for z in cam.get("zones", []):
                    if z.get("type") == "queue":
                        new_queues.append(QueueAnalyzer(
                            zone_id=z["id"],
                            name=z.get("name", z["id"]),
                            polygon=z["polygon"],
                            max_comfortable_queue=z.get("max_comfortable_queue", 4),
                            congestion_threshold_seconds=z.get("congestion_threshold_seconds", 120.0)
                        ))
                    else:
                        new_zones.append(Zone(
                            zone_id=z["id"],
                            name=z.get("name", z["id"]),
                            polygon=z["polygon"],
                            zone_type=z.get("type", "dwell")
                        ))
                ctx["zones"] = new_zones
                ctx["queues"] = new_queues
                logger.info(f"Hot-reloaded {len(new_tripwires)} tripwires and {len(new_zones) + len(new_queues)} zones for {cam_id}")

    def _generate_and_save_rollup(self, cam_id: str, ctx: Dict[str, Any], current_time: float):
        if ctx["tripwires"]:
            current_in = sum(tw.in_count for tw in ctx["tripwires"])
            current_out = sum(tw.out_count for tw in ctx["tripwires"])
            delta_in = current_in - ctx["last_in_count"]
            delta_out = current_out - ctx["last_out_count"]
            ctx["last_in_count"] = current_in
            ctx["last_out_count"] = current_out
            current_occupancy = max(0, current_in - current_out)
        else:
            # Pure Computer Vision People Tracking and Counting
            total_unique = len(ctx["tracked_ids_today"])
            delta_in = total_unique - ctx["last_unique_count"]
            ctx["last_unique_count"] = total_unique
            delta_out = 0
            current_occupancy = len(ctx.get("current_active_tracks", []))

        # Dwell calculation
        avg_dwell = 0.0
        if ctx["zones"]:
            dwells = [z.get_metrics()["avg_dwell_seconds"] for z in ctx["zones"]]
            avg_dwell = round(sum(dwells) / len(dwells), 1)
        elif ctx.get("current_active_tracks"):
            dwells = [t.last_seen - t.first_seen for t in ctx["current_active_tracks"]]
            if dwells:
                avg_dwell = round(sum(dwells) / len(dwells), 1)

        queue_len = 0
        avg_wait = 0.0
        alert_active = 0

        rollup = {
            "store_id": self.store_id,
            "device_id": self.device_id,
            "camera_id": cam_id,
            "timestamp_start": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ctx["rollup_start_time"])),
            "timestamp_end": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(current_time)),
            "in_count": delta_in,
            "out_count": delta_out,
            "current_occupancy": current_occupancy,
            "avg_dwell_seconds": avg_dwell,
            "queue_length": queue_len,
            "avg_queue_wait_seconds": avg_wait,
            "queue_alert_active": alert_active
        }

        self.local_buffer.save_rollup(rollup)
        ctx["last_rollup_time"] = current_time
        ctx["rollup_start_time"] = current_time

        logger.info(
            f"[{cam_id}] People Count: {current_occupancy} live | "
            f"New Shoppers: +{delta_in} | Total Unique: {len(ctx['tracked_ids_today'])}"
        )

    def stop(self):
        self.running = False
        logger.info("Stopping pipeline and saving state...")
        for ctx in self.camera_contexts.values():
            ctx["reader"].stop()
        self.exporter.stop()
        logger.info("EdgePipeline cleanly terminated.")

def main():
    pipeline_cfg = os.environ.get("PIPELINE_CONFIG", "configs/pipeline.yaml")
    cameras_cfg = os.environ.get("CAMERAS_CONFIG", "configs/cameras.yaml")

    pipeline = EdgePipeline(pipeline_cfg, cameras_cfg)

    def handle_signal(sig, frame):
        logger.info("Received termination signal.")
        pipeline.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    pipeline.start()

if __name__ == "__main__":
    main()

