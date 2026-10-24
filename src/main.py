import os
import sys
import copy
import time
import json
import signal
import yaml
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Any, Optional

from src.ingestion.stream_reader import StreamReader
from src.perception.detector import PersonDetector
from src.perception.tracker import SimpleByteTracker, tracker_params_for_infer_gap
from src.perception.performance import limit_cameras, resolve_performance
from src.perception.async_pose import AsyncPoseRefiner
from src.perception.detector_backend import BACKEND_RFDETR, backend_label
from src.perception.registry import ModelRegistry, ModelSpec, select_device, TIER_FAST, TIER_SLOW
from src.perception.model_stack import demographics_env_enabled, dpia_gate_ok
from src.perception.pose_estimator import PoseEstimator, match_pose_to_track
from src.perception.rtmpose_estimator import RTMPoseFootEstimator, resolve_rtmpose_onnx
from src.analytics.pose_fall_candidate import status as pose_fall_status
from src.analytics.shelf_gap_geometry import snapshot_from_products as shelf_gap_snapshot
from src.perception.face_detector import FaceDetector, face_inside_box, crop_face, align_face
from src.perception.age_gender import AgeGenderEstimator
from src.perception.head_pose import HeadPoseEstimator
from src.perception.world_detector import OpenVocabProductDetector, filter_out_persons
from src.analytics.tripwire import Tripwire
from src.analytics.zones import Zone
from src.analytics.queue_analyzer import QueueAnalyzer
from src.analytics.heatmap import Heatmap
from src.analytics.demographics import DemographicsAnalyzer
from src.analytics.groups import GroupAnalyzer
from src.analytics.attention import AttentionAnalyzer
from src.analytics.product_interest import ProductInterestAnalyzer
from src.analytics.glass_analyzer import GlassROIAnalyzer, build_glass_block
from src.analytics.floor_analytics import FloorAnalytics
from src.analytics.alerts_engine import AlertsEngine
from src.analytics.safety_analytics import SafetyAnalytics
from src.analytics.cross_camera_fusion import CrossCameraFusion, project_homography
from src.analytics.journey import build_journey_block
from src.analytics.staff_response import StaffQueueResponseTracker, build_staff_block
from src.storage.local_buffer import LocalBuffer
from src.telemetry.exporter import TelemetryExporter
from src.telemetry.health import HealthMonitor
from src.runtime_lock import acquire_runtime_lock, runtime_lock_is_held
from server.model_switches import active_model_names, read_controls
from src.visualizer.debug_overlay import DebugOverlay, resolve_overlay_box_style
from src.perception.reid import ReIdEmbedding, SoftReIdExtractor, SoftReIdGallery

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
        self.source_session_id = uuid.uuid4().hex
        self.alerts_engine = AlertsEngine()
        self.staff_response = StaffQueueResponseTracker(
            response_timeout_seconds=float(
                self.pipeline_cfg.get("analytics", {}).get("staff_response_timeout_seconds", 600.0)
            )
        )
        self.rollup_interval = self.pipeline_cfg.get("storage", {}).get("rollup_interval_seconds", 30)

        # Storage & Telemetry
        db_path = self.pipeline_cfg.get("storage", {}).get("db_path", "data/storage/edgesight.db")
        self.local_buffer = LocalBuffer(db_path=db_path)
        self.frames_dir = os.path.join(os.path.dirname(db_path), "frames")
        os.makedirs(self.frames_dir, exist_ok=True)

        cloud_endpoint = (
            os.environ.get("TELEMETRY_CLOUD_ENDPOINT")
            or self.pipeline_cfg.get("telemetry", {}).get("cloud_endpoint", "http://localhost:8000/api/v1/telemetry")
        )
        local_endpoint = (
            os.environ.get("TELEMETRY_LOCAL_ENDPOINT")
            or self.pipeline_cfg.get("telemetry", {}).get("local_endpoint", "http://localhost:8000/api/v1/telemetry")
        )
        self.exporter = TelemetryExporter(
            local_buffer=self.local_buffer,
            cloud_endpoint=cloud_endpoint,
            local_endpoint=local_endpoint,
            push_interval_seconds=self.pipeline_cfg.get("telemetry", {}).get("push_interval_seconds", 30),
            api_key=os.environ.get("EDGESIGHT_API_KEY")
        )
        self.health_monitor = HealthMonitor(self.device_id)
        self.staff_min_seconds = self.pipeline_cfg.get("analytics", {}).get("staff_min_seconds_in_zone", 10.0)
        self.heatmaps_dir = os.path.join(os.path.dirname(db_path), "heatmaps")
        os.makedirs(self.heatmaps_dir, exist_ok=True)
        self.heatmap_write_seconds = self.pipeline_cfg.get("analytics", {}).get("heatmap_write_seconds", 10.0)
        # Frame-synced live JSON for the portal (same cadence as annotated JPEG export).
        self.live_dir = os.path.join(os.path.dirname(db_path), "live")
        os.makedirs(self.live_dir, exist_ok=True)

        # Performance preset (EDGE_PERF_MODE / performance.mode). Detect
        # (yolo26s @ 640, infer every 2) is the Docker demo default — see docs/performance/live-fps.md.
        self.perf = resolve_performance(self.pipeline_cfg)
        self.perf_mode = self.perf["mode"]
        self.infer_every_n = int(self.perf["infer_every_n"])
        self.display_every_n = int(self.perf["display_every_n"])

        # Perception model (shared across cameras to optimize memory)
        p_cfg = self.pipeline_cfg.get("perception", {})
        model_name = (
            os.environ.get("EDGESIGHT_DETECT_MODEL")
            or self.perf.get("model_name")
            or p_cfg.get("model_name")
            or "models/yolo26n.pt"
        )
        # Detect mode pins person conf to 0.20–0.25. Other modes keep yaml.
        if self.perf.get("person_conf") is not None:
            conf_thresh = float(self.perf["person_conf"])
        else:
            conf_thresh = p_cfg.get("confidence_threshold", 0.50)
        object_conf = float(self.perf.get("object_conf") or p_cfg.get("object_confidence") or 0.45)
        iou_thresh = p_cfg.get("iou_threshold", 0.45)
        min_height = p_cfg.get("min_height", 85.0)
        min_width = p_cfg.get("min_width", 30.0)
        min_aspect_ratio = p_cfg.get("min_aspect_ratio", 1.0)
        max_aspect_ratio = p_cfg.get("max_aspect_ratio", 4.2)
        min_area = p_cfg.get("min_area", 3000.0)
        imgsz = int(self.perf.get("imgsz") or p_cfg.get("imgsz") or 640)
        detector_backend = self.perf.get("detector_backend") or "yolo26"

        self.detector = PersonDetector(
            model_name=model_name,
            conf_thresh=conf_thresh,
            iou_thresh=iou_thresh,
            min_height=min_height,
            min_width=min_width,
            min_aspect_ratio=min_aspect_ratio,
            max_aspect_ratio=max_aspect_ratio,
            min_area=min_area,
            # a pipeline running without a working detector would report plausible-looking zeros
            require_model=p_cfg.get("require_model", True),
            imgsz=imgsz,
            backend=detector_backend,
            rfdetr_variant=self.perf.get("rfdetr_variant"),
            rfdetr_weights=self.perf.get("rfdetr_weights"),
            pipeline_cfg=self.pipeline_cfg,
            object_conf=object_conf,
            detect_store_objects=bool(p_cfg.get("detect_store_objects", True)),
        )
        self.person_conf = float(conf_thresh)
        self.object_conf = float(object_conf)

        # Mirror person detector into the registry (ultralytics or rfdetr kind).
        self.registry = ModelRegistry(os.getcwd())
        if detector_backend == BACKEND_RFDETR:
            self.registry.register(
                ModelSpec(
                    key="person",
                    kind="rfdetr",
                    path=str(self.perf.get("rfdetr_weights") or "rf-detr-nano.pth"),
                    capability="person",
                    tier=TIER_FAST,
                    task="detect",
                    enabled=True,
                    required=bool(p_cfg.get("require_model", True)),
                    params={
                        "variant": self.perf.get("rfdetr_variant") or "nano",
                        "device": self.detector.device,
                    },
                )
            )
            # Mark already-loaded instance so status() reports loaded without double-init.
            if self.detector.is_loaded:
                self.registry._loaded["person"] = self.detector.model
                os.environ["RFDETR_RUNTIME_LOADED"] = "1"
        else:
            self.registry.register(
                ModelSpec(
                    key="person",
                    kind="ultralytics",
                    path=model_name,
                    capability="person",
                    tier=TIER_FAST,
                    task="detect",
                    enabled=True,
                    required=bool(p_cfg.get("require_model", True)),
                    params={"device": self.detector.device},
                )
            )
            if self.detector.is_loaded:
                self.registry._loaded["person"] = self.detector.model
            os.environ.pop("RFDETR_RUNTIME_LOADED", None)

        self.cameras_cfg_path = cameras_config_path
        self.last_config_mtime = os.path.getmtime(cameras_config_path) if os.path.exists(cameras_config_path) else 0
        self.last_reload_check = time.time()

        # --- Enrichment model tier -------------------------------------------
        # The fast tier above (person detection + tracking + tripwire/zone/queue) is
        # untouched. These models add the retail-analytics detail the fast tier cannot
        # see: body behaviour, head orientation, population cohorts and products.
        self.models_cfg = self.pipeline_cfg.get("models", {}) or {}
        # Enrichment tier is EXPLICIT: fast/balanced/detect force it off; quality keeps
        # the models.* yaml gating truthful (no silent re-enable). EDGE_ENRICHMENT overrides.
        _env_enrichment = os.environ.get("EDGE_ENRICHMENT")
        if _env_enrichment is not None:
            self.models_enabled = _env_enrichment not in ("", "0", "false", "False")
            logger.info(
                f"EDGE_ENRICHMENT={_env_enrichment} env override — enrichment "
                f"{'ON' if self.models_enabled else 'OFF'}"
            )
        elif self.perf_mode in ("fast", "balanced", "detect") or not self.perf.get("enrichment"):
            self.models_enabled = False
        else:
            self.models_enabled = bool(self.models_cfg.get("enabled", True))
            if self.models_enabled:
                sub_on = any(
                    bool((self.models_cfg.get(k) or {}).get("enabled"))
                    for k in ("pose", "face", "demographics", "head_pose", "products")
                )
                if not sub_on:
                    for key in ("pose", "face", "demographics", "head_pose", "products"):
                        self.models_cfg.setdefault(key, {})["enabled"] = True
                    self.models_cfg["enabled"] = True

        self.device = select_device(self.models_cfg.get("device", "auto"))
        self.enrichment_device = self._resolve_enrichment_device()
        self.enrichment_threads = int(self.models_cfg.get("enrichment_threads", 3))
        try:
            import torch
            if self.models_enabled and self.enrichment_device == "cpu":
                # Enrichment shares the machine with the detector — cap threads.
                torch.set_num_threads(self.enrichment_threads)
            elif self.perf_mode in ("fast", "balanced") and self.detector.device == "cpu":
                # Light tiers alone: give YOLO more CPU (Docker Mac ARM).
                torch.set_num_threads(max(4, int(os.environ.get("EDGE_TORCH_THREADS", "6") or 6)))
        except Exception:
            pass
        # self.registry already created with the person detector entry above.
        self.pose_estimator = None
        self.rtmpose = None
        self.rtmpose_refiner = None
        self.face_detector = None
        self.age_gender = None
        self.head_pose = None
        self.world_detector = None
        self.model_errors: Dict[str, str] = {}
        self._slow_model_locks = {
            name: threading.Lock() for name in ("pose", "face", "products", "demographics", "reid")
        }

        if self.models_enabled:
            self._init_enrichment_models()
        self._init_rtmpose()
        if self.rtmpose is not None:
            self.rtmpose_refiner = AsyncPoseRefiner(self.rtmpose)

        reid_cfg = (self.models_cfg.get("reid") or {}) if getattr(self, "models_cfg", None) is not None else {}
        # ReID is explicitly sampled at a low cadence, so it may run in fast mode
        # when both the profile and owner switch enable it. Do not silently force
        # this separate short-visit role to quality mode.
        reid_enabled = bool(reid_cfg.get("enabled", False)) and read_controls()["reid"]
        self.reid_cfg = reid_cfg
        self.reid_extractor = SoftReIdExtractor(
            weights=reid_cfg.get("weights"),
            onnx_weights=reid_cfg.get("onnx_weights"),
            device=str(reid_cfg.get("device", "cpu")),
            enabled=reid_enabled,
            base_dir=os.getcwd(),
        )
        self.reid_gallery = SoftReIdGallery(
            max_age_seconds=float(reid_cfg.get("gallery_ttl_seconds", 3600)),
        )
        fusion_cfg = self.pipeline_cfg.get("cross_camera_fusion", {}) or {}
        shared_zone_cameras: Dict[str, set] = {}
        camera_homographies: Dict[str, Any] = {}
        for camera in self.cameras_cfg.get("cameras", []) or []:
            camera_id = str(camera.get("id", ""))
            if camera.get("floor_homography") is not None:
                camera_homographies[camera_id] = camera.get("floor_homography")
            for zone in camera.get("zones", []) or []:
                if zone.get("type", "dwell") == "staff":
                    continue
                store_zone_id = zone.get("store_zone_id")
                if store_zone_id:
                    shared_zone_cameras.setdefault(str(store_zone_id), set()).add(camera_id)
        self.cross_camera_fusion = CrossCameraFusion(
            requested_enabled=bool(fusion_cfg.get("enabled", False)),
            reid_active=self.reid_extractor.active,
            shared_zone_cameras=shared_zone_cameras,
            camera_homographies=camera_homographies,
            association_window_seconds=float(fusion_cfg.get("association_window_seconds", 1.5)),
            cosine_threshold=float(fusion_cfg.get("cosine_similarity_min", 0.86)),
            max_floor_distance_m=float(fusion_cfg.get("max_floor_distance_m", 2.5)),
            gallery_ttl_seconds=float(fusion_cfg.get("gallery_ttl_seconds", 20.0)),
        )
        logger.info(
            "Cross-camera fusion requested=%s enabled=%s gate=%s mapped_zones=%s",
            bool(fusion_cfg.get("enabled", False)),
            self.cross_camera_fusion.enabled,
            self.cross_camera_fusion.gate_reason,
            len(self.cross_camera_fusion.shared_zone_cameras),
        )

        logger.info(
            "Performance mode=%s detector=%s imgsz=%s infer_every_n=%s display_every_n=%s "
            "enrichment=%s max_cameras=%s",
            self.perf_mode,
            model_name,
            imgsz,
            self.infer_every_n,
            self.display_every_n,
            self.models_enabled,
            self.perf.get("max_cameras"),
        )

        # Camera context pipelines
        self.camera_contexts: Dict[str, Dict[str, Any]] = {}
        self._init_cameras()
        self._prune_stale_live_snapshots()

        self.running = False

    def _prune_stale_live_snapshots(self):
        """Drop per-cam live/*.json for cameras not in the active set (e.g. after max_cameras)."""
        active = set(self.camera_contexts.keys())
        try:
            for name in os.listdir(self.live_dir):
                if not name.endswith(".json") or name.startswith("store") or name.endswith(".tmp.json"):
                    continue
                cam_id = name[: -len(".json")]
                if cam_id not in active:
                    try:
                        os.remove(os.path.join(self.live_dir, name))
                        logger.info("Pruned stale live snapshot %s (camera not active)", name)
                    except OSError:
                        pass
        except FileNotFoundError:
            pass

    # ------------------------------------------------------------------ models
    def _resolve_enrichment_device(self) -> str:
        """Picks the device the enrichment tier runs on.

        The enrichment tier runs in its own thread while the fast tier keeps
        inferring. PyTorch's MPS backend keeps a single Metal command buffer per
        device and is not safe to drive from two threads at once -- running the
        person detector on MPS and the enrichment models on MPS concurrently aborts
        the process with

            failed assertion _status < MTLCommandBufferStatusCommitted
            in -[IOGPUMetalCommandBuffer setCurrentCommandEncoder:]

        (reproduced by scripts/dev-tools/check_mps_concurrency.py). So when the fast tier owns
        MPS, the enrichment tier runs on the CPU instead. The enrichment tier is
        deliberately low-frequency, so CPU inference there costs nothing that matters.

        CUDA is thread-safe, so on an NVIDIA edge node both tiers can share the GPU.
        """
        configured = (self.models_cfg.get("enrichment_device", "auto") or "auto").lower()
        if configured != "auto":
            if configured == self.device == "mps":
                logger.error(
                    "enrichment_device is 'mps' while the person detector is also on 'mps'. "
                    "PyTorch's MPS backend is not thread-safe and this combination aborts the "
                    "process. Falling back to 'cpu' for the enrichment tier."
                )
                return "cpu"
            return configured

        if self.device == "mps":
            return "cpu"
        return self.device

    def _init_enrichment_models(self):
        """Registers and lazily prepares the enrichment models.

        Each model is loaded on its own so that one unavailable checkpoint (say, a
        345MB demographic model that was not downloaded) degrades that single
        capability instead of stopping the pipeline. The person detector is never
        affected -- it is not part of this tier.
        """
        pose_cfg = self.models_cfg.get("pose", {}) or {}
        face_cfg = self.models_cfg.get("face", {}) or {}
        demo_cfg = dict(self.models_cfg.get("demographics", {}) or {})
        head_cfg = self.models_cfg.get("head_pose", {}) or {}
        prod_cfg = self.models_cfg.get("products", {}) or {}

        # DPIA / k-anon latch: ENABLE_DEMOGRAPHICS defaults off — never load MiVOLO/age path live.
        if not (demographics_env_enabled() and dpia_gate_ok()):
            demo_cfg["enabled"] = False
            self.models_cfg["demographics"] = demo_cfg
            logger.info(
                "Demographics model gated off (ENABLE_DEMOGRAPHICS=%s, DPIA gate=%s). "
                "Set both the explicit enable and DPIA gate after k≥10 wiring.",
                os.environ.get("ENABLE_DEMOGRAPHICS", "0"),
                dpia_gate_ok(),
            )

        if pose_cfg.get("enabled", True):
            self.registry.register(ModelSpec(
                key="pose", kind="ultralytics", path=pose_cfg.get("weights", "models/yolo26m-pose.pt"),
                capability="pose", tier=TIER_SLOW, task="pose",
                params={"device": self.enrichment_device},
            ))
        if face_cfg.get("enabled", True):
            face_path = self._first_existing_weight(
                face_cfg.get("weights", "models/onnx/face_detection_yunet_2023mar.onnx"),
                "models/onnx/face_detection_yunet_2023mar.onnx",
                "models/pack/04-face-attr/face_detection_yunet_2023mar.onnx",
            ) or face_cfg.get("weights", "models/onnx/face_detection_yunet_2023mar.onnx")
            self.registry.register(ModelSpec(
                key="face", kind="onnx", path=face_path,
                capability="face", tier=TIER_SLOW,
                params={"intra_op_num_threads": self.enrichment_threads},
            ))
        mivolo_dir = demo_cfg.get("mivolo_directory")
        # MiVOLO and the legacy age_gender ONNX both produce age/gender
        # estimates. Load only the explicitly selected estimator.
        if demo_cfg.get("enabled", True) and not mivolo_dir:
            demo_path = self._resolve_demographics_weights(demo_cfg)
            self.registry.register(ModelSpec(
                key="demographics", kind="onnx", path=demo_path,
                capability="demographics", tier=TIER_SLOW,
                params={
                    "providers": demo_cfg.get("providers", ["CPUExecutionProvider"]),
                    "intra_op_num_threads": self.enrichment_threads,
                },
            ))
        if prod_cfg.get("enabled", True):
            backend = str(prod_cfg.get("backend", "world") or "world").lower()
            if backend == "yoloe":
                prod_path = self._first_existing_weight(
                    prod_cfg.get("shelf_weights") or prod_cfg.get("weights"),
                    "models/pack/06-shelf/yoloe-v8s-seg-pf.pt",
                    "models/yolov8s-worldv2.pt",
                    "models/pack/05-open-vocab/yolov8s-worldv2.pt",
                ) or "models/pack/06-shelf/yoloe-v8s-seg-pf.pt"
            else:
                prod_path = self._first_existing_weight(
                    prod_cfg.get("weights", "models/yolov8s-worldv2.pt"),
                    "models/yolov8s-worldv2.pt",
                    "models/pack/05-open-vocab/yolov8s-worldv2.pt",
                    "models/pack/07-openvocab/yolov8s-worldv2.pt",
                    "models/pack/06-shelf/yoloe-v8s-seg-pf.pt",
                ) or prod_cfg.get("weights", "models/yolov8s-worldv2.pt")
            self._products_backend = backend
            self._products_weights = prod_path
            self.registry.register(ModelSpec(
                key="products", kind="ultralytics", path=prod_path,
                capability="product", tier=TIER_SLOW,
                params={"device": self.enrichment_device},
            ))

        # Warm each model up front so the first real frame does not pay the load cost.
        if pose_cfg.get("enabled", True):
            model = self.registry.get("pose")
            if model is not None:
                self.pose_estimator = PoseEstimator(
                    model,
                    conf_threshold=float(pose_cfg.get("confidence", 0.30)),
                    device=self.enrichment_device,
                )
            else:
                self.model_errors["pose"] = self.registry.error("pose") or "unavailable"

        if face_cfg.get("enabled", True):
            weights = self._first_existing_weight(
                face_cfg.get("weights", "models/onnx/face_detection_yunet_2023mar.onnx"),
                "models/onnx/face_detection_yunet_2023mar.onnx",
                "models/pack/04-face-attr/face_detection_yunet_2023mar.onnx",
            ) or face_cfg.get("weights", "models/onnx/face_detection_yunet_2023mar.onnx")
            path = weights if os.path.isabs(weights) else os.path.join(os.getcwd(), weights)
            try:
                self.face_detector = FaceDetector(
                    path,
                    score_threshold=float(face_cfg.get("score_threshold", 0.55)),
                )
            except Exception as e:
                self.model_errors["face"] = str(e)
                logger.error(f"Face detector unavailable: {e}")

        if demo_cfg.get("enabled", True) and not mivolo_dir:
            session = self.registry.get("demographics")
            if session is not None:
                self.age_gender = AgeGenderEstimator(
                    session,
                    min_face_px=float(face_cfg.get("min_face_px", 30)),
                )
            else:
                self.model_errors["demographics"] = self.registry.error("demographics") or "unavailable"

        if demo_cfg.get("enabled") and mivolo_dir:
            try:
                from src.perception.mivolo_estimator import MiVoloEstimator
                self.age_gender = MiVoloEstimator(mivolo_dir)
                logger.info("MiVOLO v2 demographics estimator loaded from %s", mivolo_dir)
            except Exception as error:
                self.model_errors["mivolo_v2"] = str(error)
                logger.error("MiVOLO v2 failed: %s", error)

        if head_cfg.get("enabled", True):
            self.head_pose = HeadPoseEstimator(focal_scale=float(head_cfg.get("focal_scale", 1.0)))

        if prod_cfg.get("enabled", True):
            model = self.registry.get("products")
            if model is not None:
                self.world_detector = OpenVocabProductDetector(
                    model,
                    vocabulary=prod_cfg.get("vocabulary"),
                    conf_threshold=float(prod_cfg.get("confidence", 0.20)),
                    device=self.enrichment_device,
                    mode=getattr(self, "_products_backend", "world"),
                )
            else:
                self.model_errors["products"] = self.registry.error("products") or "unavailable"

        logger.info(
            f"Enrichment tier ready on device '{self.enrichment_device}' "
            f"(fast tier on '{self.device}'): "
            f"pose={'yes' if self.pose_estimator else 'no'}, "
            f"face={'yes' if self.face_detector else 'no'}, "
            f"demographics={'yes' if self.age_gender else 'no'}, "
            f"products={'yes' if self.world_detector else 'no'}"
        )

    def _first_existing_weight(self, *candidates: str) -> Optional[str]:
        """Return the first relative/absolute weight path that exists on disk."""
        for rel in candidates:
            if not rel:
                continue
            path = rel if os.path.isabs(rel) else os.path.join(os.getcwd(), rel)
            if os.path.isfile(path) and os.path.getsize(path) > 1000:
                return rel if not os.path.isabs(rel) else path
        return None

    @staticmethod
    def _rtmpose_on_disk() -> bool:
        return resolve_rtmpose_onnx() is not None

    def _init_rtmpose(self) -> None:
        """Load RTMPose-t/s ONNX for ankle feet (rtmlib preferred)."""
        flag = (os.environ.get("ENABLE_RTMPOSE") or "1").strip().lower()
        if flag in ("0", "false", "off", "no"):
            logger.info("RTMPose disabled (ENABLE_RTMPOSE=%s).", flag)
            return
        if not self._rtmpose_on_disk():
            logger.info("RTMPose ONNX missing — foot=bbox bottom-center.")
            return
        prefer = (os.environ.get("RTMPOSE_VARIANT") or "t").strip().lower()
        try:
            every = int(os.environ.get("RTMPOSE_EVERY_N") or "4")
        except ValueError:
            every = 4
        self.rtmpose_every_n = max(1, every)
        self.rtmpose = RTMPoseFootEstimator(
            prefer=prefer if prefer in ("t", "s", "tiny", "small") else "t",
            device="cpu",
        )
        if not self.rtmpose.active:
            self.rtmpose = None
            self.model_errors["rtmpose"] = "load_failed"
            os.environ.pop("RTMPOSE_RUNTIME_LOADED", None)
            return
        os.environ["RTMPOSE_RUNTIME_LOADED"] = "1"
        logger.info(
            "RTMPose foot estimator ON (%s, every %d frames).",
            self.rtmpose.backend,
            self.rtmpose_every_n,
        )

    def _apply_rtmpose_feet(self, tracks: List[Any], frame: Any, ctx: Dict[str, Any]) -> None:
        if self.rtmpose is None or not read_controls()["rtmpose"] or not tracks or frame is None:
            return
        every = int(getattr(self, "rtmpose_every_n", 4) or 4)
        refiner = getattr(self, "rtmpose_refiner", None)
        if refiner is not None:
            refiner.update(tracks, frame, every_n=every)

    def _resolve_demographics_weights(self, demo_cfg: Dict[str, Any]) -> str:
        """Picks the demographics checkpoint to load.

        Prefers the INT8 copy when it exists. Measured on this Mac (8-core M-series,
        CPU execution provider): FP32 493ms/face, INT8 283ms/face, with predictions
        within ~0.5 years of each other on the sample footage. The CoreML provider is
        both slower (1.3s/face) and numerically wrong for the INT8 graph, so the
        demographics session is pinned to the CPU provider in the config.
        """
        quantized = demo_cfg.get("quantized_weights")
        if quantized:
            q_path = quantized if os.path.isabs(quantized) else os.path.join(os.getcwd(), quantized)
            if os.path.exists(q_path):
                logger.info(f"Using INT8 demographics checkpoint: {quantized}")
                return quantized
        return demo_cfg.get("weights", "models/onnx/age_gender_vit.onnx")

    def _load_yaml(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            logger.warning(f"Config file not found at {path}. Using defaults.")
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    def _build_analytics(self, cam: Dict[str, Any]):
        tripwires = []
        for tw in cam.get("tripwires", []):
            tripwires.append(Tripwire(
                wire_id=tw["id"],
                name=tw.get("name", tw["id"]),
                line=tw["line"],
                in_direction=tw.get("in_direction", "top_to_bottom")
            ))

        grace = self.pipeline_cfg.get("analytics", {}).get("zone_exit_grace_seconds", 3.0)
        zones = []
        queues = []
        staff_zones = []
        glass_rois: List[GlassROIAnalyzer] = []
        for z in cam.get("zones", []):
            ztype = z.get("type", "dwell")
            if ztype == "staff":
                sz = Zone(
                    zone_id=z["id"],
                    name=z.get("name", z["id"]),
                    polygon=z["polygon"],
                    zone_type="staff",
                    exit_grace_seconds=grace
                )
                sz.expected_on_post = z.get("expected_on_post")
                sz.linked_queue_ids = list(z.get("linked_queue_ids") or [])
                sz.store_zone_id = z.get("store_zone_id")
                staff_zones.append(sz)
            elif ztype == "queue":
                queue = QueueAnalyzer(
                    zone_id=z["id"],
                    name=z.get("name", z["id"]),
                    polygon=z["polygon"],
                    max_comfortable_queue=z.get("max_comfortable_queue", 4),
                    congestion_threshold_seconds=z.get("congestion_threshold_seconds", 120.0),
                    exit_grace_seconds=grace,
                    service_point=z.get("service_point"),
                    alert_wait_ms=z.get("alert_wait_ms"),
                    alert_length=z.get("alert_length"),
                    staff_zone_id=z.get("staff_zone_id"),
                )
                queue.store_zone_id = z.get("store_zone_id")
                queues.append(queue)
            elif ztype == "glass":
                glass_rois.append(GlassROIAnalyzer(
                    glass_id=z["id"],
                    name=z.get("name", z["id"]),
                    polygon=z["polygon"],
                    min_stop_seconds=float(z.get("min_stop_seconds", 5.0) or 5.0),
                    entry_attribution_seconds=float(z.get("entry_attribution_seconds", 90.0) or 90.0),
                    exit_grace_seconds=grace,
                ))
            else:
                zone = Zone(
                    zone_id=z["id"],
                    name=z.get("name", z["id"]),
                    polygon=z["polygon"],
                    zone_type=ztype,
                    exit_grace_seconds=grace
                )
                zone.store_zone_id = z.get("store_zone_id")
                if z.get("zone_capacity_people") is not None:
                    zone.zone_capacity_people = z.get("zone_capacity_people")
                if z.get("blocked_grace_seconds") is not None:
                    zone.blocked_grace_seconds = z.get("blocked_grace_seconds")
                if z.get("entry_grace_seconds") is not None:
                    zone.entry_grace_seconds = z.get("entry_grace_seconds")
                zones.append(zone)

        for g in cam.get("glass_views") or []:
            poly = g.get("polygon")
            if not poly or len(poly) < 3:
                continue
            glass_rois.append(GlassROIAnalyzer(
                glass_id=g.get("id") or f"glass_{len(glass_rois)+1}",
                name=g.get("name") or g.get("id") or "Glass",
                polygon=poly,
                min_stop_seconds=float(g.get("min_stop_seconds", 5.0) or 5.0),
                entry_attribution_seconds=float(g.get("entry_attribution_seconds", 90.0) or 90.0),
                exit_grace_seconds=grace,
            ))
        return tripwires, zones, queues, staff_zones, glass_rois

    @staticmethod
    def _calibration_signature(cam: Dict[str, Any]) -> str:
        return json.dumps({
            "tripwires": cam.get("tripwires", []),
            "zones": cam.get("zones", []),
            "glass_views": cam.get("glass_views", []),
            "floor_homography": cam.get("floor_homography"),
        }, sort_keys=True)

    def _make_tracker(self) -> SimpleByteTracker:
        """ByteTrack knobs aligned with ``infer_every_n`` (skipped frames break IDs)."""
        t_cfg = self.pipeline_cfg.get("tracking", {}) or {}
        perf_cfg = getattr(self, "perf", {}) or {}
        scaled = tracker_params_for_infer_gap(
            int(getattr(self, "infer_every_n", 1) or 1),
            track_buffer=int(t_cfg.get("track_buffer", 45)),
            match_thresh=float(t_cfg.get("match_thresh", 0.45)),
            min_hits=int(t_cfg.get("min_hits", 4)),
            track_thresh=float(
                perf_cfg["track_thresh"]
                if perf_cfg.get("track_thresh") is not None
                else t_cfg.get("track_thresh", 0.5)
            ),
        )
        return SimpleByteTracker(
            max_age=scaled["max_age"],
            iou_threshold=scaled["iou_threshold"],
            min_hits=scaled["min_hits"],
            stationary_policy=t_cfg.get("stationary_policy", "tag"),
            track_thresh=scaled["track_thresh"],
            dist_gate=scaled["dist_gate"],
            pred_dist_gate=scaled["pred_dist_gate"],
            infer_every_n=scaled["infer_every_n"],
        )

    def _refresh_cross_camera_fusion(self) -> None:
        """Rebuild fusion gates after camera coverage or homography config changes."""
        if not hasattr(self, "reid_extractor"):
            return
        fusion_cfg = self.pipeline_cfg.get("cross_camera_fusion", {}) or {}
        shared_zone_cameras: Dict[str, set] = {}
        camera_homographies: Dict[str, Any] = {}
        for camera in self.cameras_cfg.get("cameras", []) or []:
            camera_id = str(camera.get("id", ""))
            if camera.get("floor_homography") is not None:
                camera_homographies[camera_id] = camera.get("floor_homography")
            for zone in camera.get("zones", []) or []:
                if zone.get("type", "dwell") == "staff":
                    continue
                store_zone_id = zone.get("store_zone_id")
                if store_zone_id:
                    shared_zone_cameras.setdefault(str(store_zone_id), set()).add(camera_id)
        self.cross_camera_fusion = CrossCameraFusion(
            requested_enabled=bool(fusion_cfg.get("enabled", False)),
            reid_active=self.reid_extractor.active,
            shared_zone_cameras=shared_zone_cameras,
            camera_homographies=camera_homographies,
            association_window_seconds=float(fusion_cfg.get("association_window_seconds", 1.5)),
            cosine_threshold=float(fusion_cfg.get("cosine_similarity_min", 0.86)),
            max_floor_distance_m=float(fusion_cfg.get("max_floor_distance_m", 2.5)),
            gallery_ttl_seconds=float(fusion_cfg.get("gallery_ttl_seconds", 20.0)),
        )
        logger.info(
            "Cross-camera fusion refreshed enabled=%s gate=%s mapped_zones=%s",
            self.cross_camera_fusion.enabled,
            self.cross_camera_fusion.gate_reason,
            len(self.cross_camera_fusion.shared_zone_cameras),
        )

    def _build_camera_context(self, cam: Dict[str, Any]) -> Dict[str, Any]:
        cam_id = cam["id"]
        source = cam.get("source", "")
        fps_target = int(cam.get("fps_target", 15))

        # Never chase FPS the source cannot deliver (sample videos are 15 fps; decode
        # and inference each add their own caps downstream). Clamp once, up front.
        if source and not source.startswith(("rtsp://", "rtsps://", "http://")):
            src_fps = 0.0
            try:
                probe = cv2.VideoCapture(source)
                if probe.isOpened():
                    src_fps = float(probe.get(cv2.CAP_PROP_FPS) or 0.0)
                probe.release()
            except Exception:
                src_fps = 0.0
            if src_fps >= 1.0:
                clamped = int(min(fps_target, max(1, round(src_fps))))
                if clamped != fps_target:
                    logger.info(
                        f"[{cam_id}] fps_target {fps_target} -> {clamped} "
                        f"(source caps at {src_fps:.1f} fps)"
                    )
                    fps_target = clamped

        tripwires, zones, queues, staff_zones, glass_rois = self._build_analytics(cam)

        demo_cfg = (getattr(self, "models_cfg", {}) or {}).get("demographics", {}) or {}
        prod_cfg = (getattr(self, "models_cfg", {}) or {}).get("products", {}) or {}

        return {
            "camera_id": cam_id,
            "name": cam.get("name", cam_id),
            "source": source,
            "fps_target": fps_target,
            "floor_homography": cam.get("floor_homography"),
            "calibration_sig": self._calibration_signature(cam),
            "reader": StreamReader(camera_id=cam_id, source=source, fps_target=fps_target),
            "tracker": self._make_tracker(),
            "tripwires": tripwires,
            "zones": zones,
            "queues": queues,
            "staff_zones": staff_zones,
            "glass_rois": glass_rois,
            "floor": FloorAnalytics(),
            "safety": SafetyAnalytics(),
            "recent_trip_in": {},
            "staff_ids": set(),
            "staff_visible": 0,
            "tracked_ids_today": set(),
            "reader_loop_seen": 0,
            "unique_total_all_passes": 0,
            "sim_pass_history": [],
            "heatmap": None,
            "last_heatmap_write": 0.0,
            "last_unique_count": 0,
            "current_active_tracks": [],
            "last_rollup_time": time.time(),
            "rollup_start_time": time.time(),
            "frames_processed": 0,
            "processed_fps": 0.0,
            "display_fps": 0.0,
            "fps_window_start": time.time(),
            "fps_window_frames": 0,
            "display_window_start": time.time(),
            "display_window_frames": 0,
            "last_in_count": 0,
            "last_out_count": 0,
            # --- Enrichment tier state ---
            "demographics": DemographicsAnalyzer(
                k_anonymity=int(demo_cfg.get("k_anonymity", 10)),
                smoothing_alpha=float(demo_cfg.get("smoothing_alpha", 0.35)),
                window_seconds=float(demo_cfg.get("window_seconds", 3600.0)),
            ),
            "groups": GroupAnalyzer(),
            "attention": AttentionAnalyzer(),
            "products": ProductInterestAnalyzer(
                engagement_radius_px=float(prod_cfg.get("engagement_radius_px", 160)),
                min_dwell_seconds=float(prod_cfg.get("min_dwell_seconds", 1.0)),
            ),
            "frame_lock": threading.Lock(),
            "latest_frame": None,
            "last_slow_frame_idx": -1,
            "slow_ticks": 0,
            "demo_cursor": 0,
            "slow_thread": None,
            "display_thread": None,
        }

    def _init_cameras(self):
        cams = list(self.cameras_cfg.get("cameras", []))
        max_cameras = (getattr(self, "perf", {}) or {}).get("max_cameras")
        limited = limit_cameras(cams, max_cameras)
        if len(limited) < len(cams):
            logger.info(
                "EDGE_MAX_CAMERAS / performance.max_cameras=%s — using %s of %s cameras for FPS budget",
                max_cameras,
                len(limited),
                len(cams),
            )
        for cam in limited:
            self.camera_contexts[cam["id"]] = self._build_camera_context(cam)
            logger.info(f"Initialized pipeline for camera: {cam.get('name', cam['id'])} ({cam['id']})")

    @staticmethod
    def _display_tracks_at_time(tracks: List[Any], frame_time: float, frame_shape: Any) -> List[Any]:
        """Project cached boxes a short distance for display between detector passes.

        Projection is display-only; analytics and tracking continue to use observed
        boxes. The 0.35 s / 30%-height caps prevent stale tracks from drifting away.
        """
        height, width = frame_shape[:2]
        projected = []
        for track in tracks:
            dt = min(0.35, max(0.0, frame_time - float(getattr(track, "last_seen", frame_time))))
            velocity = getattr(track, "velocity", (0.0, 0.0)) or (0.0, 0.0)
            dx, dy = float(velocity[0]) * dt, float(velocity[1]) * dt
            box = list(getattr(track, "bbox", []) or [])
            if len(box) >= 4:
                box_h = max(1.0, float(box[3]) - float(box[1]))
                distance = (dx * dx + dy * dy) ** 0.5
                limit = min(float(max(width, height)), box_h * 0.30)
                if distance > limit and distance > 0:
                    dx, dy = dx * limit / distance, dy * limit / distance
                if dt > 0:
                    shown = copy.copy(track)
                    shown.bbox = [
                        max(0.0, min(float(width), float(box[0]) + dx)),
                        max(0.0, min(float(height), float(box[1]) + dy)),
                        max(0.0, min(float(width), float(box[2]) + dx)),
                        max(0.0, min(float(height), float(box[3]) + dy)),
                    ]
                    pose_foot = getattr(track, "pose_foot", None)
                    if pose_foot is not None:
                        shown.pose_foot = (
                            max(0.0, min(float(width), float(pose_foot[0]) + dx)),
                            max(0.0, min(float(height), float(pose_foot[1]) + dy)),
                        )
                    projected.append(shown)
                    continue
            projected.append(track)
        return projected

    def _start_display_tier(self, ctx: Dict[str, Any]) -> None:
        """Publish each unique captured frame independently of model inference."""
        cam_id = ctx.get("camera_id", "camera")

        def _worker():
            last_frame_idx = -1
            while self.running and ctx["reader"].running:
                item = ctx["reader"].peek_latest_frame()
                if item is None or item[0] == last_frame_idx:
                    time.sleep(0.004)
                    continue
                frame_idx, stamp, frame = item
                last_frame_idx = frame_idx
                frame_time = stamp.utc if hasattr(stamp, "utc") else float(stamp)
                tracks = self._display_tracks_at_time(
                    list(ctx.get("last_overlay_tracks") or []), frame_time, frame.shape
                )
                try:
                    draw_kwargs = dict(
                        frame=frame,
                        tracks=tracks,
                        tripwires=list(ctx.get("tripwires") or []),
                        zones=list(ctx.get("zones") or []),
                        queues=list(ctx.get("queues") or []),
                        camera_name=ctx["name"],
                        fps=ctx["reader"].fps_actual,
                        infer_fps=ctx.get("processed_fps", 0.0),
                    )
                    try:
                        annotated = DebugOverlay.draw_pipeline(
                            **draw_kwargs,
                            staff_zones=list(ctx.get("staff_zones") or []),
                            staff_ids=set(ctx.get("staff_ids") or set()),
                            objects=list(ctx.get("last_overlay_objects") or []),
                        )
                    except TypeError:
                        annotated = DebugOverlay.draw_pipeline(**draw_kwargs)
                    frame_path = os.path.join(self.frames_dir, f"{cam_id}.jpg")
                    tmp_path = os.path.join(self.frames_dir, f"{cam_id}.tmp.jpg")
                    if cv2.imwrite(tmp_path, annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 70]):
                        os.replace(tmp_path, frame_path)
                        ctx["display_window_frames"] = int(ctx.get("display_window_frames", 0) or 0) + 1
                        dwin = time.time() - float(ctx.get("display_window_start", time.time()))
                        if dwin >= 2.0:
                            ctx["display_fps"] = round(ctx["display_window_frames"] / dwin, 1)
                            ctx["display_window_start"] = time.time()
                            ctx["display_window_frames"] = 0
                except Exception as e:
                    logger.debug("Frame publish error for %s: %s", cam_id, e)

        thread = threading.Thread(target=_worker, name=f"Display-{cam_id}", daemon=True)
        ctx["display_thread"] = thread
        thread.start()
        logger.info("Independent live display publisher started for camera '%s'.", cam_id)

    def start(self):
        self.running = True
        self.exporter.start()

        import threading as _threading
        reg = _threading.Thread(target=self._device_registration_loop, name="DeviceRegister", daemon=True)
        reg.start()

        for ctx in self.camera_contexts.values():
            ctx["reader"].start()
            self._start_slow_tier(ctx)
            self._start_display_tier(ctx)

        logger.info(f"AD Labs EdgeSight running for store '{self.store_id}'. Processing active streams...")

        try:
            while self.running:
                loop_start = time.time()
                for cam_id, ctx in self.camera_contexts.items():
                    item = ctx["reader"].get_latest_frame(timeout=0.01)
                    if item is None:
                        continue

                    frame_idx, stamp, frame = item
                    # stamp.utc = wall clock (tripwire/zones); stamp.mono = interval-safe
                    frame_time = stamp.utc if hasattr(stamp, "utc") else float(stamp)
                    frame_time_mono = getattr(stamp, "mono", frame_time)
                    ctx["frames_processed"] += 1
                    ctx["last_capture_ts_utc"] = frame_time
                    ctx["last_capture_ts_mono"] = frame_time_mono

                    # Display vs analytics cadence: decode every frame for a smooth MJPEG
                    # path; run detect+track only every infer_every_n frames.
                    do_infer = (ctx["frames_processed"] % self.infer_every_n) == 0

                    controls = read_controls()
                    if (self.models_enabled or bool(getattr(self.reid_extractor, "active", False))) and any(
                        controls[key] for key in ("pose", "face", "products", "demographics", "reid")
                    ):
                        # Publish the frame for the enrichment tier. The slow worker runs
                        # in its own thread, so it gets its own copy: the debug overlay
                        # draws on this buffer in place and a half-drawn frame would be
                        # nonsense to a face model.
                        with ctx["frame_lock"]:
                            ctx["latest_frame"] = (frame_idx, frame_time, frame_time_mono, frame.copy())

                    if do_infer:
                        # Inference throughput (frames actually run through detect+track).
                        ctx["fps_window_frames"] += 1
                        window = time.time() - ctx["fps_window_start"]
                        if window >= 2.0:
                            ctx["processed_fps"] = round(ctx["fps_window_frames"] / window, 1)
                            ctx["fps_window_start"] = time.time()
                            ctx["fps_window_frames"] = 0

                        # 1. Perception — Ultralytics YOLO people (+ COCO store objects for overlay)
                        controls = read_controls()
                        if not controls["person_detector"]:
                            detections, store_objects = [], []
                        elif hasattr(self.detector, "detect_frame"):
                            detections, store_objects = self.detector.detect_frame(frame)
                        else:
                            detections = self.detector.detect(frame)
                            store_objects = []
                        # Open-vocab (YOLOE / YOLO-World) labels when enrichment last wrote them.
                        ov_objects = list(ctx.get("last_overlay_objects_ov") or [])
                        ctx["last_overlay_objects"] = list(store_objects) + ov_objects

                        # 2. Tracking (people only — store objects are visual labels)
                        active_tracks = ctx["tracker"].update(detections, frame_time)
                        # 2b. RTMPose ankle feet (red mark / tripwire / dwell) when ONNX present
                        self._apply_rtmpose_feet(active_tracks, frame, ctx)
                        # Early tracks (≥2 hits): tripwire needs ground-point history during
                        # min_hits confirmation or entrance crossings are lost forever.
                        early_tracks = ctx["tracker"].early_tracks()
                        customers = self._update_analytics(
                            cam_id,
                            ctx,
                            active_tracks,
                            frame_time,
                            frame=frame,
                            early_tracks=early_tracks,
                        )
                    else:
                        active_tracks = list(ctx.get("last_overlay_tracks") or [])

                    # Frame-synced live JSON follows detector/tracker updates. The
                    # annotated feed is published by its own unique-frame worker.
                    if do_infer or (ctx["frames_processed"] % max(2, self.display_every_n * 2)) == 0:
                        try:
                            self._write_live_snapshot(cam_id, ctx, frame_time)
                        except Exception as e:
                            logger.debug(f"Live snapshot error for {cam_id}: {e}")

                    # 5. Check for Periodic Rollup Export
                    if do_infer and frame_time - ctx["last_rollup_time"] >= self.rollup_interval:
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

    def _update_analytics(
        self,
        cam_id: str,
        ctx: Dict[str, Any],
        active_tracks: List[Any],
        frame_time: float,
        frame: Any = None,
        early_tracks: Optional[List[Any]] = None,
    ) -> List[Any]:
        """Update the camera's staff, crossing, zone, queue, safety and heatmap state.

        Kept as one testable operation so both the live loop and deterministic track
        tests exercise the exact same staff-exclusion and customer-only analytics.
        """
        reader = ctx.get("reader")
        loop_count = int(getattr(reader, "loop_count", 0) or 0)
        if loop_count != ctx.get("reader_loop_seen", 0):
            self._reset_sim_pass(cam_id, ctx, loop_count)

        for staff_zone in ctx.get("staff_zones", []):
            staff_zone.update(active_tracks, frame_time)
            for tid, entered in staff_zone.active_tracks_in_zone.items():
                if frame_time - entered >= self.staff_min_seconds:
                    ctx["staff_ids"].add(tid)

        customers = [track for track in active_tracks if track.track_id not in ctx["staff_ids"]]
        crossing_tracks = early_tracks if early_tracks is not None else active_tracks
        crossing_customers = [track for track in crossing_tracks if track.track_id not in ctx["staff_ids"]]
        for track in customers:
            track.dwell_s = 0.0
            track.zone_id = None
        ctx["current_active_tracks"] = customers
        ctx["last_overlay_tracks"] = active_tracks
        ctx["staff_visible"] = len(active_tracks) - len(customers)

        ctx["tracked_ids_today"].update(track.track_id for track in customers)
        # A local track may be tagged as staff only after its dwell verification window.
        # Remove it from the per-pass visitor set once that tag becomes stable.
        ctx["tracked_ids_today"].difference_update(ctx["staff_ids"])

        crossing_events: List[Dict[str, Any]] = []
        for tripwire in ctx.get("tripwires", []):
            crossing_events.extend(tripwire.update(crossing_customers, frame_time))
        if crossing_events:
            self._persist_crossing_events(cam_id, crossing_events)
            recent = ctx.setdefault("recent_trip_in", {})
            for event in crossing_events:
                direction = str(event.get("direction", "")).lower()
                if direction in ("in", "trip_in", "enter") and event.get("track_id") is not None:
                    recent[int(event["track_id"])] = float(event.get("timestamp") or frame_time)
            cutoff = frame_time - 120.0
            for track_id in list(recent):
                if recent[track_id] < cutoff:
                    del recent[track_id]

        for zone in ctx.get("zones", []):
            zone.update(customers, frame_time)

        staff_on_post = int(ctx.get("staff_visible", 0) or 0)
        analytic_events: List[Dict[str, Any]] = []
        for queue in ctx.get("queues", []):
            try:
                analytic_events.extend(queue.update(customers, frame_time, staff_on_post=staff_on_post) or [])
            except TypeError:
                queue.update(customers, frame_time)
        for glass in ctx.get("glass_rois") or []:
            analytic_events.extend(
                glass.update(
                    customers,
                    frame_time,
                    recent_trip_in_ids=ctx.get("recent_trip_in") or {},
                ) or []
            )

        floor = ctx.get("floor")
        if floor is not None:
            if frame is not None:
                try:
                    floor.set_frame_size(float(frame.shape[1]), float(frame.shape[0]))
                except Exception:
                    pass
            floor.update(customers, list(ctx.get("zones") or []), frame_time)

        safety = ctx.get("safety")
        if safety is not None:
            safety.update(customers, list(ctx.get("zones") or []), frame_time, cam_id)
        if analytic_events and hasattr(self, "_persist_analytic_events"):
            self._persist_analytic_events(cam_id, analytic_events)

        if frame is not None:
            if ctx.get("heatmap") is None:
                ctx["heatmap"] = Heatmap(frame.shape[1], frame.shape[0])
            ctx["heatmap"].add(customers, frame_time)
            if cv2 is not None and frame_time - ctx.get("last_heatmap_write", 0.0) >= self.heatmap_write_seconds:
                self._write_heatmap(cam_id, ctx, frame, frame_time)
        return customers

    # --------------------------------------------------------- enrichment tier
    @staticmethod
    def _run_independent_model_jobs(
        jobs: Dict[str, Callable[[], Any]],
        max_workers: int = 3,
    ) -> Dict[str, Any]:
        """Run independent per-frame model calls concurrently; isolate one model failure."""
        if not jobs:
            return {}
        results: Dict[str, Any] = {}
        worker_count = max(1, min(int(max_workers), len(jobs)))
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="edge-model") as pool:
            futures = {pool.submit(job): name for name, job in jobs.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as exc:  # one unavailable model must not suppress peers
                    logger.warning("Slow model %s pass failed: %s", name, exc)
        return results

    def _run_locked_model(self, name: str, job: Callable[[], Any]) -> Any:
        """Serialize calls into shared model instances while different models overlap."""
        lock = self._slow_model_locks.setdefault(name, threading.Lock())
        with lock:
            return job()

    def _start_slow_tier(self, ctx: Dict[str, Any]):
        """Starts the enrichment worker for one camera.

        The enrichment models (pose, face, demographics, products) cost far more per
        frame than person detection. Running them inline would cut the throughput of
        the core counters, so they get their own thread and their own frame copy.
        The fast tier therefore keeps its latency while the enrichment tier catches up
        on its own cadence.
        """
        reid_active = bool(getattr(getattr(self, "reid_extractor", None), "active", False))
        if not getattr(self, "models_enabled", False) and not reid_active:
            return
        if self.pose_estimator is None and self.face_detector is None \
                and self.age_gender is None and self.world_detector is None and not reid_active:
            logger.warning("Enrichment tier enabled but no enrichment model loaded; skipping.")
            return

        interval = int((self.models_cfg.get("slow_tier", {}) or {}).get("interval_frames", 4))
        cam_id = ctx.get("camera_id", "camera")

        def _worker():
            while self.running:
                with ctx["frame_lock"]:
                    latest = ctx["latest_frame"]
                if latest is None:
                    time.sleep(0.05)
                    continue
                frame_idx, frame_time, frame_time_mono, frame = latest
                # Honour the configured cadence. The frame index counts decoded frames,
                # so this is "every N video frames" regardless of how fast inference runs.
                if frame_idx - ctx["last_slow_frame_idx"] < interval:
                    time.sleep(0.01)
                    continue
                ctx["last_slow_frame_idx"] = frame_idx
                try:
                    self._process_slow_tier(cam_id, ctx, frame_time, frame, frame_time_mono)
                    ctx["slow_ticks"] += 1
                except Exception as e:
                    logger.error(f"Enrichment pass failed on {cam_id}: {e}", exc_info=True)

        thread = threading.Thread(target=_worker, name=f"Enrichment-{cam_id}", daemon=True)
        ctx["slow_thread"] = thread
        thread.start()
        logger.info(f"Enrichment tier started for camera '{cam_id}' (every {interval} frames).")

    def _process_slow_tier(
        self,
        cam_id: str,
        ctx: Dict[str, Any],
        frame_time: float,
        frame: Any,
        frame_time_mono: Optional[float] = None,
    ):
        """One enrichment pass: pose, face, head pose, demographics, groups, attention.

        Everything produced here is ephemeral. No face crop, landmark, embedding or
        per-person estimate is written to disk or sent anywhere -- only aggregate
        cohorts, group sizes and engagement counters leave this function.
        """
        tracks = list(ctx.get("current_active_tracks", []))
        if not tracks:
            return

        frame_h, frame_w = frame.shape[:2]
        slow_cfg = self.models_cfg.get("slow_tier", {}) or {}
        pose_cfg = self.models_cfg.get("pose", {}) or {}
        face_cfg = self.models_cfg.get("face", {}) or {}
        prod_cfg = self.models_cfg.get("products", {}) or {}
        controls = read_controls()

        # Pose and face detection can consume the same immutable frame together.
        # A lock per shared model protects a reused instance across camera workers.
        model_jobs: Dict[str, Callable[[], Any]] = {}
        if self.pose_estimator is not None and controls["pose"]:
            model_jobs["pose"] = lambda: self._run_locked_model(
                "pose", lambda: self.pose_estimator.estimate(frame)
            )
        if self.face_detector is not None and controls["face"]:
            model_jobs["faces"] = lambda: self._run_locked_model(
                "face", lambda: self.face_detector.detect(frame)
            )
        model_outputs = self._run_independent_model_jobs(
            model_jobs,
            max_workers=int(slow_cfg.get("parallel_model_workers", 3) or 3),
        )

        # --- 1. Pose: what the body is doing ---------------------------------
        pose_by_track: Dict[int, Dict[str, Any]] = {}
        if "pose" in model_outputs:
            iou_min = float(pose_cfg.get("match_iou", 0.30))
            for pose in model_outputs["pose"]:
                best_track = None
                best_iou = 0.0
                for track in tracks:
                    iou = match_pose_to_track(pose, track.bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_track = track
                if best_track is not None and best_iou >= iou_min:
                    pose_by_track[best_track.track_id] = pose

        # --- 2. Faces: assign a face to the body it belongs to -------------
        face_by_track: Dict[int, Dict[str, Any]] = {}
        faces = model_outputs.get("faces", [])
        if faces:
            for face in faces:
                for track in tracks:
                    if face_inside_box(face, track.bbox):
                        # Keep the largest (closest) face if several match one body.
                        existing = face_by_track.get(track.track_id)
                        if existing is None or face["width"] * face["height"] > existing["width"] * existing["height"]:
                            face_by_track[track.track_id] = face
                        break

        # Wide-angle store cameras put faces at 20-40px, which YuNet can miss at
        # frame level. Re-running it on an upscaled person crop recovers them.
        if self.face_detector is not None and controls["face"] and bool(face_cfg.get("upscale_crops", True)):
            max_crops = int(slow_cfg.get("max_faces_per_tick", 8))
            missing = [t for t in tracks if t.track_id not in face_by_track]
            for track in missing[:max_crops]:
                for face in self.face_detector.detect_in_crop(frame, track.bbox):
                    if face["width"] < float(face_cfg.get("min_face_px", 30)):
                        continue
                    face_by_track[track.track_id] = face
                    break

        # --- 3. Head pose + demographics -----------------------------------
        head_by_track: Dict[int, Dict[str, Any]] = {}
        if self.head_pose is not None:
            for track_id, face in face_by_track.items():
                pose = self.head_pose.estimate(face, frame_w, frame_h)
                if pose is not None:
                    head_by_track[track_id] = pose

        predictions: Dict[int, Dict[str, Any]] = {}
        selected = []
        crops = []
        if self.age_gender is not None and controls["demographics"] and face_by_track:
            max_faces = int(slow_cfg.get("max_faces_per_tick", 2))
            # Rotate the sampled faces every tick. The demographic model is the most
            # expensive step in the tier (~0.28s/face on CPU), so only a couple of
            # faces are inferred per pass; without rotation the same two people
            # would monopolise the budget and the rest of the store would never
            # get sampled. The per-track EMA in DemographicsAnalyzer accumulates
            # the readings over time.
            candidates = list(face_by_track.items())
            cursor = int(ctx.get("demo_cursor", 0)) % max(1, len(candidates))
            rotated = candidates[cursor:] + candidates[:cursor]
            selected = rotated[:max_faces]
            ctx["demo_cursor"] = (cursor + max_faces) % max(1, len(candidates))

            align = bool(face_cfg.get("align", True))
            for _track_id, face in selected:
                crop = None
                if align:
                    crop = align_face(frame, face)
                if crop is None:
                    crop = crop_face(frame, face)
                crops.append(crop)
        # The product model, demographics model, and OSNet consume independent
        # inputs now. Run them side by side after face-to-track assignment, while
        # keeping each underlying model instance serialized across camera threads.
        followup_jobs: Dict[str, Callable[[], Any]] = {}
        if self.age_gender is not None and controls["demographics"] and crops:
            followup_jobs["demographics"] = lambda: self._run_locked_model(
                "demographics", lambda: self.age_gender.predict_batch(crops)
            )
        if self.world_detector is not None and controls["products"]:
            followup_jobs["products"] = lambda: self._run_locked_model(
                "products", lambda: self.world_detector.detect(frame)
            )
        if self.reid_extractor.active and controls["reid"]:
            followup_jobs["reid"] = lambda: self._run_locked_model(
                "reid",
                lambda: self._sample_soft_reid(
                    cam_id, ctx, tracks, frame, frame_time, frame_time_mono
                ),
            )
        followup_outputs = self._run_independent_model_jobs(
            followup_jobs,
            max_workers=int(slow_cfg.get("parallel_model_workers", 3) or 3),
        )
        results = followup_outputs.get("demographics", [])
        for (track_id, _face), prediction in zip(selected, results):
            predictions[track_id] = prediction

        demographics = ctx["demographics"]
        for track_id, prediction in predictions.items():
            demographics.observe(track_id, prediction, frame_time)

        # --- 4. Engagement --------------------------------------------------
        attention = ctx["attention"]
        for track in tracks:
            pose = pose_by_track.get(track.track_id)
            head = head_by_track.get(track.track_id)
            attention.observe(
                track_id=track.track_id,
                timestamp=frame_time,
                attention_score=head["attention_score"] if head else None,
                facing_camera=head["facing_camera"] if head else None,
                phone_in_hand=pose["phone_in_hand"] if pose else None,
                in_zone=self._track_in_zone(ctx, track),
            )

        # --- 5. Social grouping ---------------------------------------------
        ctx["groups"].update(tracks)

        # --- 6. Product interest --------------------------------------------
        if "products" in followup_outputs:
            detections = followup_outputs["products"]
            # A shopper wearing a jacket is not a product on display.
            detections = filter_out_persons(
                detections,
                [t.bbox for t in tracks],
                max_overlap=float(prod_cfg.get("max_person_overlap", 0.5)),
            )
            max_products = int(slow_cfg.get("max_products_per_tick", 24))
            kept = detections[:max_products]
            ctx["products"].observe(kept, tracks, frame_time)
            # Feed open-vocab class names into the MJPEG overlay (person boxes stay on tracks).
            ctx["last_overlay_objects_ov"] = kept
        elif not controls["products"]:
            ctx["products"].reset()
            ctx["last_overlay_objects_ov"] = []
        # --- 7. Housekeeping -------------------------------------------------
        active_ids = [t.track_id for t in tracks]
        demographics.prune(active_ids, frame_time)
        attention.prune(active_ids)
        ctx["groups"].prune(active_ids)
        ctx["products"].prune(active_ids)


    def _sample_soft_reid(self, cam_id, ctx, tracks, frame, frame_time, frame_time_mono=None):
        if not self.reid_extractor.active or not tracks:
            return
        interval = int(getattr(self, "reid_cfg", {}).get("interval_frames", 16))
        last = int(ctx.get("last_reid_frame_idx", -10**9))
        frame_idx = int(ctx.get("last_slow_frame_idx", 0) or 0)
        if frame_idx - last < interval:
            return
        ctx["last_reid_frame_idx"] = frame_idx
        max_crops = int(getattr(self, "reid_cfg", {}).get("max_crops_per_tick", 4))
        h, w = frame.shape[:2]
        crops, chosen = [], []
        for track in tracks[:max_crops]:
            x1, y1, x2, y2 = [int(v) for v in track.bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 - x1 < 16 or y2 - y1 < 32:
                continue
            crops.append(frame[y1:y2, x1:x2].copy())
            chosen.append(track)
        if not crops:
            return
        feats = self.reid_extractor.extract_crops(crops)
        if feats is None:
            return
        for track, emb in zip(chosen, feats):
            foot = getattr(track, "foot_point", None)
            self.reid_gallery.add(ReIdEmbedding(
                camera_id=cam_id, track_id=int(track.track_id), embedding=emb,
                capture_ts_utc=float(frame_time),
                foot_xy=(float(foot[0]), float(foot[1])) if foot is not None else None,
                capture_ts_mono=float(frame_time_mono) if frame_time_mono is not None else None,
            ))
            if self.cross_camera_fusion.enabled and foot is not None and frame_time_mono is not None:
                from src.analytics.zones import point_in_polygon

                shared_zone_ids = []
                for zone in list(ctx.get("zones", []) or []):
                    shared_id = getattr(zone, "store_zone_id", None)
                    if shared_id and point_in_polygon(foot, zone.polygon):
                        shared_zone_ids.append(str(shared_id))
                for queue in list(ctx.get("queues", []) or []):
                    queue_zone = getattr(queue, "zone", None)
                    shared_id = getattr(queue, "store_zone_id", None)
                    if shared_id and queue_zone is not None and point_in_polygon(foot, queue_zone.polygon):
                        shared_zone_ids.append(str(shared_id))
                floor_xy = project_homography(foot, ctx.get("floor_homography"))
                self.cross_camera_fusion.observe(
                    camera_id=cam_id,
                    track_id=int(track.track_id),
                    embedding=emb,
                    timestamp_mono=float(frame_time_mono),
                    store_zone_ids=shared_zone_ids,
                    floor_xy=floor_xy,
                )

    @staticmethod
    def _track_in_zone(ctx: Dict[str, Any], track: Any) -> bool:
        """True when a shopper's feet are inside any configured region of interest.

        Queue zones count too. A shopper standing at the checkout is inside a
        configured region just as much as one browsing the floor, and the
        engagement metric is about "attending the space you are standing in".
        Only dwell zones land in ctx["zones"]; queues are tracked separately by
        the QueueAnalyzer, so both have to be consulted here.
        """
        from src.analytics.zones import point_in_polygon

        foot = track.foot_point
        for zone in ctx.get("zones", []):
            if point_in_polygon(foot, zone.polygon):
                return True
        for queue in ctx.get("queues", []):
            if point_in_polygon(foot, queue.zone.polygon):
                return True
        return False

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
        """Reconciles running cameras with the config file: adds new cameras, removes
        deleted ones, restarts a camera whose source/FPS changed (fresh tracker and
        counters -- it's a different scene), and swaps calibration in place otherwise."""
        cams_list = [c for c in new_cfg.get("cameras", []) if c.get("id")]
        # Honor EDGE_MAX_CAMERAS / performance.max_cameras on hot-reload too
        # (otherwise calib saves re-add cams and collapse Docker CPU FPS).
        cams_list = limit_cameras(cams_list, (getattr(self, "perf", {}) or {}).get("max_cameras"))
        new_cams = {c["id"]: c for c in cams_list}

        for cam_id in list(self.camera_contexts):
            if cam_id not in new_cams:
                old = self.camera_contexts.pop(cam_id)
                self._generate_and_save_rollup(cam_id, old, time.time())
                old["reader"].stop()
                logger.info(f"Camera {cam_id} removed from config; stopped.")

        for cam_id, cam in new_cams.items():
            ctx = self.camera_contexts.get(cam_id)

            if ctx is None:
                self.camera_contexts[cam_id] = self._build_camera_context(cam)
                if self.running:
                    self.camera_contexts[cam_id]["reader"].start()
                    self._start_slow_tier(self.camera_contexts[cam_id])
                    self._start_display_tier(self.camera_contexts[cam_id])
                logger.info(f"Camera {cam_id} added from config.")
                continue

            if cam.get("source", "") != ctx["source"] or cam.get("fps_target", 15) != ctx["fps_target"]:
                self._generate_and_save_rollup(cam_id, ctx, time.time())
                display_thread = ctx.get("display_thread")
                ctx["reader"].stop()
                if display_thread is not None and display_thread.is_alive():
                    display_thread.join(timeout=1.0)
                self.camera_contexts[cam_id] = self._build_camera_context(cam)
                if self.running:
                    self.camera_contexts[cam_id]["reader"].start()
                    self._start_slow_tier(self.camera_contexts[cam_id])
                    self._start_display_tier(self.camera_contexts[cam_id])
                logger.info(f"Camera {cam_id} source changed: {ctx['source']} -> {cam.get('source', '')}")
                continue

            ctx["name"] = cam.get("name", cam_id)
            if self._calibration_signature(cam) != ctx["calibration_sig"]:
                # Flush the old counters first, then reset the delta baselines: the new
                # Tripwire objects start at zero, so a stale last_in_count would make the
                # next rollup's delta negative.
                self._generate_and_save_rollup(cam_id, ctx, time.time())
                ctx["tripwires"], ctx["zones"], ctx["queues"], ctx["staff_zones"], ctx["glass_rois"] = self._build_analytics(cam)
                ctx["floor_homography"] = cam.get("floor_homography")
                ctx["calibration_sig"] = self._calibration_signature(cam)
                ctx["last_in_count"] = 0
                ctx["last_out_count"] = 0
                ctx["staff_ids"] = set()
                logger.info(
                    f"Hot-reloaded {len(ctx['tripwires'])} tripwires and "
                    f"{len(ctx['zones']) + len(ctx['queues']) + len(ctx.get('staff_zones', []))} zones for {cam_id}"
                )

        self.cameras_cfg = new_cfg
        self._refresh_cross_camera_fusion()

    def _write_heatmap(self, cam_id: str, ctx: Dict[str, Any], frame: Any, frame_time: float):
        """Renders the camera's heatmap over the current clean (un-annotated) frame and writes it
        atomically, for GET /api/v1/heatmap/{camera_id}."""
        ctx["last_heatmap_write"] = frame_time
        try:
            path = os.path.join(self.heatmaps_dir, f"{cam_id}.jpg")
            tmp = os.path.join(self.heatmaps_dir, f"{cam_id}.tmp.jpg")
            cv2.imwrite(tmp, ctx["heatmap"].render(frame), [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            os.replace(tmp, path)
        except Exception as e:
            logger.debug(f"Heatmap export error for {cam_id}: {e}")


    def _write_live_snapshot(self, cam_id: str, ctx: Dict[str, Any], frame_time: float):
        """Writes the current in-memory analytics to disk for /api/v1/live.

        Occupancy here is active customer tracks (matches the YOLO HUD), not tripwire
        IN−OUT net — looping sample footage makes net occupancy misleading.
        """
        controls = read_controls()
        customers = list(ctx.get("current_active_tracks", []))
        tripwire_in = sum(tw.in_count for tw in ctx.get("tripwires", []))
        tripwire_out = sum(tw.out_count for tw in ctx.get("tripwires", []))

        queue_len = 0
        avg_wait = 0.0
        alert_active = False
        queues_out = []
        for q in ctx.get("queues", []):
            m = q.get_metrics()
            queues_out.append({
                "id": getattr(q, "zone_id", None) or getattr(q, "id", "queue"),
                "name": getattr(q, "name", "queue"),
                "store_zone_id": getattr(q, "store_zone_id", None),
                "queue_length": m.get("queue_length", 0),
                "avg_wait_seconds": m.get("avg_wait_seconds", 0.0),
                "alert_active": bool(m.get("alert_active")),
                # Episode tier pass-through (join/leave machinery feeds /live.queue)
                "now": m.get("now"),
                "kpi": m.get("kpi"),
                "series": m.get("series"),
                "recent_episodes": m.get("recent_episodes"),
                "abandon_status": m.get("abandon_status"),
                "abandon_note": m.get("abandon_note"),
                "staff_zone_id": m.get("staff_zone_id"),
                "alert_wait_ms": m.get("alert_wait_ms"),
                "alert_length": m.get("alert_length"),
                "max_capacity": m.get("max_capacity"),
            })
            queue_len = max(queue_len, m.get("queue_length", 0))
            avg_wait = max(avg_wait, m.get("avg_wait_seconds", 0.0))
            alert_active = alert_active or bool(m.get("alert_active"))

        zones_out = []
        dwells = []
        for z in ctx.get("zones", []):
            try:
                m = z.get_metrics(now=frame_time) if hasattr(z, "get_metrics") else {}
            except TypeError:
                m = z.get_metrics() if hasattr(z, "get_metrics") else {}
            dwell = float(m.get("avg_dwell_seconds", 0.0) or 0.0)
            if dwell > 0:
                dwells.append(dwell)
            visits = int(m.get("total_visits", m.get("visits", 0)) or 0)
            row = {
                "id": getattr(z, "zone_id", None) or getattr(z, "id", "zone"),
                "name": getattr(z, "name", "zone"),
                "type": getattr(z, "zone_type", None) or getattr(z, "type", "dwell"),
                "store_zone_id": getattr(z, "store_zone_id", None),
                "occupancy": m.get("current_occupancy", m.get("occupancy", 0)),
                "visits": visits,
                "total_visits": visits,
                "avg_dwell_seconds": dwell,
                "active_dwell_seconds": m.get("active_dwell_seconds") or [],
                "dwell_by_track": m.get("dwell_by_track") or {},
            }
            for attr in ("journey_stage", "stage_tag"):
                val = getattr(z, attr, None)
                if val:
                    row[attr] = val
            zones_out.append(row)

        staff_zones = []
        staff_block_zones = []
        for z in ctx.get("staff_zones", []):
            tagged = len(getattr(z, "active_tracks_in_zone", {}) or {})
            expected = getattr(z, "expected_on_post", None)
            if expected is None:
                state = "UNCALIBRATED"
            elif tagged >= int(expected):
                state = "COVERED"
            else:
                state = "UNDERSTAFFED"
            row = {
                "id": getattr(z, "zone_id", None) or getattr(z, "id", "staff"),
                "name": getattr(z, "name", "staff"),
                "type": "staff",
                "tagged_ids": tagged,
                "staff_present": tagged,
                "expected_on_post": expected,
                "state": state,
                "understaffed_since": None,
                "linked_queue_ids": list(getattr(z, "linked_queue_ids", []) or []),
                "camera_id": cam_id,
            }
            staff_zones.append(row)
            staff_block_zones.append(row)

        attention = ctx["attention"].snapshot() if ctx.get("attention") else {}
        groups = ctx["groups"].snapshot() if ctx.get("groups") else {}

        products_top = None
        if controls.get("products", False) and ctx.get("products"):
            prod_snap = ctx["products"].snapshot()
            products = prod_snap.get("products") or []
            if products:
                products_top = [
                    {
                        "category": p["category"],
                        "viewers": int(p.get("viewers", 0) or 0),
                        "avg_dwell_seconds": float(p.get("avg_dwell_seconds", 0.0) or 0.0),
                        "detections": int(p.get("detections", 0) or 0),
                    }
                    for p in products[:8]
                ]
        if products_top is not None and len(products_top) == 0:
            products_top = None
        # Join a category to a shelf/display only when the current product box is
        # physically inside a client-drawn display zone. Category totals remain
        # useful on their own, but we never guess which fixture they belong to.
        if products_top:
            from src.analytics.zones import point_in_polygon

            shelf_zones = [
                zone for zone in ctx.get("zones", [])
                if any(word in str(getattr(zone, "name", "")).lower() for word in ("shelf", "display", "fixture"))
            ]
            labels_to_zones: Dict[str, set] = {}
            for obj in list(ctx.get("last_overlay_objects_ov") or []):
                bbox = obj.get("bbox") or []
                label = str(obj.get("label") or "").strip()
                if not label or len(bbox) != 4:
                    continue
                center = ((float(bbox[0]) + float(bbox[2])) / 2, (float(bbox[1]) + float(bbox[3])) / 2)
                for zone in shelf_zones:
                    if point_in_polygon(center, zone.polygon):
                        labels_to_zones.setdefault(label, set()).add(str(getattr(zone, "name", zone.zone_id)))
            for product in products_top:
                product["shelf_zones"] = sorted(labels_to_zones.get(str(product.get("category") or ""), set()))
        reid_status = self.reid_extractor.status() if getattr(self, "reid_extractor", None) else {}
        slow_loaded = {
            "pose": getattr(self, "pose_estimator", None) is not None,
            "face": getattr(self, "face_detector", None) is not None,
            "demographics": getattr(self, "age_gender", None) is not None,
            "head_pose": getattr(self, "head_pose", None) is not None,
            "products": getattr(self, "world_detector", None) is not None,
            "reid": bool(reid_status.get("active")),
        }
        slow_controls = {**controls, "head_pose": controls.get("face", False)}
        active_slow_models = active_model_names(slow_loaded, slow_controls)
        rtmpose_active = bool(getattr(self, "rtmpose", None)) and controls.get("rtmpose", False)

        glass_block = build_glass_block(list(ctx.get("glass_rois") or []))
        if glass_block is None:
            entrance_block = {
                "glass": None,
                "stop_rate": None,
                "conversion_glass_to_entry": None,
                "glass_entrants": None,
                "status": "FUTURE",
                "badge_copy": (
                    "Mark glass: Set up zones → draw polygon → type glass "
                    "(or add glass_views in cameras.yaml). Null until then — nothing invented."
                ),
                "settling": False,
            }
        else:
            entrance_block = {
                "glass": glass_block,
                "stop_rate": glass_block.get("stop_rate"),
                "conversion_glass_to_entry": glass_block.get("conversion_glass_to_entry"),
                "glass_entrants": glass_block.get("glass_entrants"),
                "status": "LIVE",
                "badge_copy": (
                    "Measured 0 — glass ROI live, no glass entrants yet."
                    if (glass_block.get("glass_entrants") or 0) == 0
                    else None
                ),
                "settling": glass_block.get("settling"),
            }
        floor_block = ctx["floor"].snapshot(list(ctx.get("zones") or []), frame_time) if ctx.get("floor") else None
        safety_block = ctx["safety"].snapshot() if ctx.get("safety") else {"active": [], "note": "no safety evaluator"}
        staff_block = build_staff_block(
            staff_block_zones,
            self.staff_response,
            queues_out,
            list(ctx.get("staff_zones") or []),
            frame_time,
        )
        alerts_block = self.alerts_engine.evaluate({
            "queues": queues_out,
            "queue_length": queue_len,
            "queue_alert_active": alert_active,
            "staff_zones": staff_zones,
            "staff": staff_block,
            "safety": safety_block,
        }, now=frame_time)
        active_tracks_by_camera = {
            camera_id: [int(track.track_id) for track in camera_ctx.get("current_active_tracks", [])]
            for camera_id, camera_ctx in self.camera_contexts.items()
        }
        from src.analytics.zones import point_in_polygon

        active_store_zones: Dict[str, Dict[int, List[str]]] = {}
        for camera_id, camera_ctx in self.camera_contexts.items():
            zone_map: Dict[int, List[str]] = {}
            configured_zones = list(camera_ctx.get("zones", []) or [])
            configured_zones.extend(
                getattr(queue, "zone", None)
                for queue in list(camera_ctx.get("queues", []) or [])
            )
            for track in camera_ctx.get("current_active_tracks", []) or []:
                foot = getattr(track, "foot_point", None)
                if foot is None:
                    continue
                mapped = []
                for zone in configured_zones:
                    store_zone_id = getattr(zone, "store_zone_id", None)
                    polygon = getattr(zone, "polygon", None)
                    if store_zone_id and polygon and point_in_polygon(foot, polygon):
                        mapped.append(str(store_zone_id))
                if mapped:
                    zone_map[int(track.track_id)] = mapped
            active_store_zones[camera_id] = zone_map
        fusion_block = self.cross_camera_fusion.snapshot(
            active_tracks_by_camera,
            active_store_zones=active_store_zones,
        )

        payload = {
            "store_id": self.store_id,
            "device_id": self.device_id,
            "camera_id": cam_id,
            "camera_name": ctx.get("name", cam_id),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "video_loop": {
                "loop_count": int(getattr(ctx.get("reader"), "loop_count", 0) or 0),
                "is_simulated": bool(getattr(ctx.get("reader"), "is_file", False)),
                "unique_this_pass": len(ctx.get("tracked_ids_today", set()) or set()),
                "unique_total_all_passes": int(ctx.get("unique_total_all_passes", 0) or 0),
                "source_fps": float(getattr(ctx.get("reader"), "source_fps", 0.0) or 0.0),
                "counting_mode": (
                    "per_pass (sample video replays)"
                    if getattr(ctx.get("reader"), "is_file", False)
                    else "tripwire_cumulative"
                ),
            },
            "frame_time": frame_time,
            "people_now": len(customers),
            "staff_now": int(ctx.get("staff_visible", 0) or 0),
            "unique_tracks_today": len(ctx.get("tracked_ids_today", set())),
            "total_visitors": tripwire_in,
            "total_exits": tripwire_out,
            "net_occupancy": len(customers),
            "avg_dwell_seconds": round(sum(dwells) / len(dwells), 1) if dwells else (
                round(
                    sum(t.last_seen - t.first_seen for t in customers) / len(customers),
                    1,
                )
                if customers
                else 0.0
            ),
            "queue_length": queue_len,
            "avg_queue_wait_seconds": round(avg_wait, 1),
            "queue_alert_active": alert_active,
            "decode_fps": round(float(getattr(ctx.get("reader"), "fps_actual", 0.0) or 0.0), 1),
            "infer_fps": round(float(ctx.get("processed_fps", 0.0) or 0.0), 1),
            "display_fps": round(float(ctx.get("display_fps", 0.0) or 0.0), 1),
            "overlay_box_style": resolve_overlay_box_style(),
            "tripwires": [
                {
                    "id": getattr(tw, "wire_id", None) or getattr(tw, "id", "tw"),
                    "name": getattr(tw, "name", "tripwire"),
                    "in_count": tw.in_count,
                    "out_count": tw.out_count,
                    "session_in": int(getattr(tw, "session_in", tw.in_count) or 0),
                    "session_out": int(getattr(tw, "session_out", tw.out_count) or 0),
                }
                for tw in ctx.get("tripwires", [])
            ],
            "session_in": tripwire_in,
            "session_out": tripwire_out,
            "queues": queues_out,
            "zones": zones_out,
            "staff_zones": staff_zones,
            "journey": build_journey_block(zones_out),
            "products_top": products_top,
            "entrance": entrance_block,
            "stop_rate": entrance_block.get("stop_rate"),
            "floor": floor_block,
            "staff": staff_block,
            "safety": safety_block,
            "alerts": alerts_block,
            "fusion": fusion_block,
            "shelf_gap": shelf_gap_snapshot(list(ctx.get("last_overlay_objects_ov") or [])),
            "pose_fall": pose_fall_status(
                pose_weights_on_disk=self._rtmpose_on_disk(),
                wired=bool(getattr(self, "rtmpose", None)) or bool(self.pose_estimator),
            ),
            "field_status": {
                "demographics": "GATED" if not demographics_env_enabled() else "PARTIAL",
                "shelf_gap_geometry": "PARTIAL",
                "pose_fall_candidate": pose_fall_status(
                    pose_weights_on_disk=self._rtmpose_on_disk(),
                    wired=bool(getattr(self, "rtmpose", None)) or bool(self.pose_estimator),
                ).get("status", "FUTURE"),
                "locateanything_3b": "FUTURE",
                "entrance_stop_rate": entrance_block.get("status", "FUTURE"),
                "floor_paths": (floor_block or {}).get("status", "LIVE"),
                "queue_episodes": "LIVE",
                "queue_abandon": "PARTIAL" if any(q.get("abandon_status") == "PARTIAL" for q in queues_out) else "LIVE",
                "queue_p95": (
                    "LIVE"
                    if any((q.get("kpi") or {}).get("p95_available") for q in queues_out)
                    else "EMPTY"
                ),
                "staff": staff_block.get("status") or "LIVE",
                "staff_response_time": staff_block.get("status") or "EMPTY",
                "safety": "LIVE",
                "alerts": "LIVE",
                "multi_store": "FUTURE",
                "cross_camera_fusion": "LIVE" if fusion_block.get("enabled") else "GATED",
                "display_interest": "LIVE" if products_top else "PARTIAL",
            },
            "engagement": {
                "avg_attention_score": attention.get("avg_attention_score", 0.0),
                "facing_ratio": attention.get("facing_ratio", 0.0),
                "engaged_ratio": attention.get("engaged_ratio", 0.0),
                "group_count": groups.get("group_count", 0),
            },
            "models": {
                "person_detector": backend_label(
                    getattr(self.detector, "backend", "yolo26"),
                    getattr(self.detector, "rfdetr_variant", None),
                )
                if getattr(self.detector, "backend", "") == BACKEND_RFDETR
                else os.path.basename(
                    getattr(self.detector, "model_name", "") or "unknown"
                ).replace(".pt", ""),
                "detector_backend": getattr(self.detector, "backend", "yolo26"),
                "rfdetr_variant": getattr(self.detector, "rfdetr_variant", None)
                if getattr(self.detector, "backend", "") == BACKEND_RFDETR
                else None,
                "detector_loaded": bool(getattr(self.detector, "is_loaded", False)),
                "illumination_mode": getattr(self.detector, "last_illumination_mode", "normal"),
                "imgsz": int(getattr(self.detector, "imgsz", 0) or 0) or None,
                "tracker": "bytetrack",
                "controls": controls,
                "perf_mode": getattr(self, "perf_mode", "balanced"),
                "infer_every_n": int(getattr(self, "infer_every_n", 1) or 1),
                "person_conf": round(float(getattr(self, "person_conf", 0.0) or 0.0), 3),
                "object_conf": round(float(getattr(self, "object_conf", 0.0) or 0.0), 3),
                "overlay_box_style": resolve_overlay_box_style(),
                "enrichment": bool(active_slow_models),
                "pose_model_loaded": bool(getattr(self, "pose_estimator", None)),
                "pose": rtmpose_active or (slow_loaded["pose"] and controls.get("pose", False)),
                "rtmpose": rtmpose_active,
                "rtmpose_backend": getattr(getattr(self, "rtmpose", None), "backend", None),
                "rtmpose_calls": int(getattr(getattr(self, "rtmpose", None), "calls", 0) or 0),
                "face_boxes": slow_loaded["face"] and controls.get("face", False),
                "products_loaded": slow_loaded["products"],
                "products": slow_loaded["products"] and controls.get("products", False),
                "products_backend": getattr(self, "_products_backend", None),
                "clip_vit_enabled": bool(
                    getattr(self, "world_detector", None)
                    and controls.get("products", False)
                    and getattr(self.world_detector, "_classes_set", False)
                    and not getattr(self.world_detector, "_prompt_free", False)
                ),
                "osnet_reid_enabled": slow_loaded["reid"] and controls.get("reid", False),
                "mivolo_v2_enabled": bool(
                    getattr(self, "age_gender", None)
                    and self.age_gender.__class__.__name__ == "MiVoloEstimator"
                    and controls.get("demographics", False)
                    and demographics_env_enabled()
                    and dpia_gate_ok()
                ),
                "mivolo_v2_calls": int(getattr(getattr(self, "age_gender", None), "calls", 0) or 0),
                "slow_scheduler": {
                    "state": (
                        "running"
                        if active_slow_models and getattr(ctx.get("slow_thread"), "is_alive", lambda: False)()
                        else ("ready" if active_slow_models else "paused")
                    ),
                    "execution": "bounded-worker-pool",
                    "parallel_workers": int(
                        (self.models_cfg.get("slow_tier", {}) or {}).get("parallel_model_workers", 3) or 3
                    ),
                    "interval_frames": int(
                        (self.models_cfg.get("slow_tier", {}) or {}).get("interval_frames", 4) or 4
                    ),
                    "ticks_completed": int(ctx.get("slow_ticks", 0) or 0),
                    "enabled_models": active_slow_models,
                    "note": "Lists loaded models whose operator switches are on. Jobs run at the configured cadence; the bounded worker pool does not guarantee every model runs at once.",
                },
                "demographics_enabled": bool(
                    getattr(self, "age_gender", None)
                    and controls.get("demographics", False)
                    and demographics_env_enabled()
                    and dpia_gate_ok()
                ),
                "face_identity": False,
                "stack_policy": "docs/models/model-stack-policy.md",
                "note": (
                    f"perf={getattr(self, 'perf_mode', 'balanced')}: "
                    f"backend={getattr(self.detector, 'backend', 'yolo26')}; "
                    f"overlay={resolve_overlay_box_style()}; "
                    "person detect+track+foot zones"
                    + ("; rtmpose on" if rtmpose_active else "; foot=bbox")
                    + ("; enrichment on" if active_slow_models else "; enrichment off")
                    + ". Face boxes (if on) = k-anon age/gender only — no face ID. "
                    "Soft ReID session-scoped only. products_top = open-vocab categories, not POS SKUs. "
                    + (
                        " MiVOLO v2 is active; output remains k-anonymous."
                        if getattr(self, "age_gender", None)
                        and self.age_gender.__class__.__name__ == "MiVoloEstimator"
                        and controls.get("demographics", False)
                        and demographics_env_enabled()
                        and dpia_gate_ok()
                        else " MiVOLO v2 is not active."
                    )
                ),
            },
            "perf_mode": getattr(self, "perf_mode", "balanced"),
            "reid": {
                "active": bool(reid_status.get("active")),
                "backend": reid_status.get("backend"),
                "gallery_size": self.reid_gallery.size() if self.reid_gallery else 0,
                "session_scoped": True,
                "cross_cam_fusion": bool(fusion_block.get("enabled")),
            },
            "track_ids": [t.track_id for t in customers[:40]],
            "tracks": [
                t.to_live_dict() if hasattr(t, "to_live_dict") else {
                    "id": int(t.track_id),
                    "track_id": int(t.track_id),
                    "first_seen": float(getattr(t, "first_seen", 0) or 0),
                    "last_seen": float(getattr(t, "last_seen", 0) or 0),
                    "dwell_s": round(float(getattr(t, "dwell_s", 0) or 0), 2),
                    "ground_point": list(getattr(t, "ground_point", getattr(t, "foot_point", (0, 0)))),
                }
                for t in customers[:40]
            ],
        }

        cam_path = os.path.join(self.live_dir, f"{cam_id}.json")
        tmp_path = os.path.join(self.live_dir, f"{cam_id}.tmp.json")
        with open(tmp_path, "w") as f:
            json.dump(payload, f)
        os.replace(tmp_path, cam_path)

        # Store-wide aggregate (sum of per-cam snapshots on disk)
        store = {
            "store_id": self.store_id,
            "device_id": self.device_id,
            "timestamp": payload["timestamp"],
            "cameras": [],
            "people_now": 0,
            "staff_now": 0,
            "total_visitors": 0,
            "total_exits": 0,
            "net_occupancy": 0,
            "queue_length": 0,
            "avg_queue_wait_seconds": 0.0,
            "queue_alert_active": False,
            "avg_dwell_seconds": 0.0,
            "decode_fps": payload["decode_fps"],
            "infer_fps": payload["infer_fps"],
            "display_fps": payload.get("display_fps"),
            "source": "live_snapshot",
            "models": payload.get("models"),
            "perf_mode": payload.get("perf_mode"),
            "engagement": payload.get("engagement"),
            "reid": payload.get("reid"),
            "fusion": payload.get("fusion"),
            "products_top": payload.get("products_top"),
        }
        dwell_acc = []
        active = set(self.camera_contexts.keys())
        for name in os.listdir(self.live_dir):
            if not name.endswith(".json") or name.startswith("store") or name.endswith(".tmp.json"):
                continue
            cam_key = name[: -len(".json")]
            if active and cam_key not in active:
                continue
            try:
                with open(os.path.join(self.live_dir, name)) as f:
                    row = json.load(f)
            except Exception:
                continue
            store["cameras"].append(row.get("camera_id"))
            store["people_now"] += int(row.get("people_now", 0) or 0)
            store["staff_now"] += int(row.get("staff_now", 0) or 0)
            store["total_visitors"] += int(row.get("total_visitors", 0) or 0)
            store["total_exits"] += int(row.get("total_exits", 0) or 0)
            store["net_occupancy"] += int(row.get("net_occupancy", 0) or 0)
            store["queue_length"] = max(store["queue_length"], int(row.get("queue_length", 0) or 0))
            store["avg_queue_wait_seconds"] = max(
                store["avg_queue_wait_seconds"],
                float(row.get("avg_queue_wait_seconds", 0) or 0),
            )
            store["queue_alert_active"] = store["queue_alert_active"] or bool(row.get("queue_alert_active"))
            if row.get("avg_dwell_seconds"):
                dwell_acc.append(float(row["avg_dwell_seconds"]))
            store["infer_fps"] = max(store["infer_fps"], float(row.get("infer_fps", 0) or 0))
            store["decode_fps"] = max(store["decode_fps"], float(row.get("decode_fps", 0) or 0))
            store["display_fps"] = max(
                float(store.get("display_fps") or 0),
                float(row.get("display_fps", 0) or 0),
            )
            if row.get("models"):
                store["models"] = row["models"]
            if row.get("engagement"):
                store["engagement"] = row["engagement"]
            if row.get("reid"):
                store["reid"] = row["reid"]
            if row.get("fusion"):
                store["fusion"] = row["fusion"]
            if row.get("products_top"):
                store["products_top"] = row["products_top"]
            if row.get("entrance"):
                store["entrance"] = row["entrance"]
                store["stop_rate"] = row.get("stop_rate")
            if row.get("floor"):
                store["floor"] = row["floor"]
            if row.get("staff"):
                store["staff"] = row["staff"]
            if row.get("safety"):
                store["safety"] = row["safety"]
            if row.get("alerts"):
                store["alerts"] = row["alerts"]
            if row.get("field_status"):
                store["field_status"] = row["field_status"]
            if row.get("queues"):
                store["queues"] = row["queues"]
        if dwell_acc:
            store["avg_dwell_seconds"] = round(sum(dwell_acc) / len(dwell_acc), 1)
        fusion = store.get("fusion") or {}
        if fusion.get("enabled") and fusion.get("deduplicated_active_count") is not None:
            store["camera_people_sum"] = store["people_now"]
            store["people_now"] = int(fusion["deduplicated_active_count"])
            store["net_occupancy"] = int(fusion["deduplicated_active_count"])
            store["occupancy_mode"] = "overlap_reid_union"
            store["occupancy_note"] = (
                "Shared calibrated zones use session-scoped ReID union; unmatched tracks remain separate. "
                "Per-camera values remain available in per_camera."
            )
        else:
            store["occupancy_mode"] = "sum"
            store["occupancy_note"] = (
                "Per-camera occupancies are summed; overlapping views may double-count until calibration and ReID gates pass."
            )

        store_tmp = os.path.join(self.live_dir, "store.tmp.json")
        store_path = os.path.join(self.live_dir, "store.json")
        with open(store_tmp, "w") as f:
            json.dump(store, f)
        os.replace(store_tmp, store_path)

    def _reset_sim_pass(self, cam_id: str, ctx: Dict[str, Any], loop_count: int):
        """Loop boundary on a replaying sample video: archive this pass's uniques and
        reset per-pass counters so 'unique shoppers' counts real new appearances only.

        Cumulative style metrics (heatmap, attention, engagement) keep accruing;
        everything answering 'how many shoppers today/entered' becomes per-pass + archived.
        """
        archived = len(ctx.get("tracked_ids_today", set()) or set())
        self.cross_camera_fusion.reset()
        ctx["unique_total_all_passes"] = int(ctx.get("unique_total_all_passes", 0) or 0) + archived
        ctx["tracked_ids_today"] = set()
        ctx["reader_loop_seen"] = loop_count
        ctx["last_unique_count"] = 0
        ctx["last_in_count"] = 0
        ctx["last_out_count"] = 0
        ctx["recent_trip_in"] = {}
        ctx["staff_ids"] = set()

        for tw in ctx.get("tripwires", []):
            reset_tw = getattr(tw, "reset_pass", None)
            if callable(reset_tw):
                try:
                    reset_tw()
                    continue
                except Exception:
                    pass
            try:
                tw.in_count = 0
                tw.out_count = 0
                if hasattr(tw, "session_in"):
                    tw.session_in = 0
                if hasattr(tw, "session_out"):
                    tw.session_out = 0
                crossed = getattr(tw, "_crossed_track_ids", None)
                if crossed is not None:
                    crossed.clear()
            except Exception:
                pass

        # Fresh identities on the next pass — lingering IDs across a video loop
        # cause LOS/trajectory glitches and suppress re-crossings.
        try:
            tracker = ctx.get("tracker")
            if tracker is not None and hasattr(tracker, "reset"):
                tracker.reset()
            else:
                ctx["tracker"] = self._make_tracker()
        except Exception:
            ctx["tracker"] = self._make_tracker()
        ctx["current_active_tracks"] = []
        ctx["last_overlay_tracks"] = []

        for z in list(ctx.get("zones", []) or []) + list(ctx.get("staff_zones", []) or []):
            reset = getattr(z, "reset_pass", None)
            if callable(reset):
                try:
                    reset()
                except Exception:
                    pass
                continue
            try:
                z.active_tracks_in_zone.clear()
                z.completed_dwells.clear()
            except Exception:
                pass

        for q in list(ctx.get("queues", []) or []):
            reset = getattr(q, "reset_pass", None)
            if callable(reset):
                try:
                    reset()
                except Exception:
                    pass
                continue
            try:
                q.zone.active_tracks_in_zone.clear()
                q.zone.completed_dwells.clear()
                q._episodes.clear()
                q._completed.clear()
                q._series.clear()
                q.queue_length = 0
                q.avg_wait_seconds = 0.0
                q.alert_active = False
            except Exception:
                pass

        ctx.setdefault("sim_pass_history", []).append({
            "loop_count": loop_count,
            "archived_unique": archived,
            "total_all_passes": ctx["unique_total_all_passes"],
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        logger.info(
            f"[{cam_id}] Sample loop #{loop_count} boundary — per-pass counters reset "
            f"({archived} uniques archived, {ctx['unique_total_all_passes']} total across passes)"
        )

    def _device_registration_loop(self):
        import time as _time
        while self.running:
            try:
                self._register_device()
            except Exception as e:
                logger.debug(f"Device register skipped: {e}")
            _time.sleep(60.0)

    def _register_device(self):
        """Self-register the edge node so the cloud device panel runs on measured truth."""
        import platform as _platform
        import urllib.request as _urllib
        endpoint = os.environ.get("TELEMETRY_CLOUD_ENDPOINT", "")
        if not endpoint or not endpoint.endswith("api/v1/telemetry"):
            return
        base = endpoint[: -len("api/v1/telemetry")].rstrip("/")
        try:
            dev = str(getattr(self.detector, "device", "cpu") or "cpu")
        except Exception:
            dev = "cpu"
        engine = "PyTorch MPS (native)" if dev == "mps" else f"PyTorch {dev} (edge)"
        try:
            import torch as _torch
            torch_version = getattr(_torch, "__version__", None)
        except Exception:
            torch_version = None
        payload = {
            "device_id": self.device_id,
            "device_name": f"{_platform.node()} (Edge Node)",
            "inference_engine": engine,
            "perf_mode": getattr(self, "perf_mode", "balanced"),
            "cameras": len(self.camera_contexts),
            "python_version": _platform.python_version(),
            "torch_version": torch_version,
        }
        req = _urllib.Request(
            base + "/api/v1/device/register",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **({"X-API-Key": os.environ["EDGESIGHT_API_KEY"]} if os.environ.get("EDGESIGHT_API_KEY") else {})},
        )
        _urllib.urlopen(req, timeout=3).read()
        logger.info(f"Device registered with cloud: {self.device_id} ({engine})")

    def _persist_crossing_events(self, cam_id: str, events: List[Dict[str, Any]]):
        """Persists individual tripwire crossings as durable events, independent of
        the periodic rollup aggregation, so a crash between rollup flushes cannot
        lose the underlying crossings."""
        for event in events:
            self.local_buffer.save_event({
                "store_id": self.store_id,
                "device_id": self.device_id,
                "camera_id": cam_id,
                "wire_id": event["wire_id"],
                "track_id": event["track_id"],
                "direction": event["direction"],
                "event_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(event["timestamp"]))
            })

    def _persist_analytic_events(self, cam_id: str, events: List[Dict[str, Any]]):
        """Persist additive glass/queue events on the durable channel (non-trip)."""
        skip = {"glass_stop_reached", "queue_wait_ms_reached", "glass_roi_ping"}
        for event in events:
            et = event.get("event") or event.get("direction")
            if et in skip:
                continue
            tid = event.get("track_id")
            if tid is None:
                tid = 0
            ts = event.get("timestamp") or time.time()
            try:
                self.local_buffer.save_event({
                    "store_id": self.store_id,
                    "device_id": self.device_id,
                    "camera_id": cam_id,
                    "wire_id": event.get("wire_id") or event.get("glass_id") or event.get("queue_id") or et,
                    "track_id": int(tid),
                    "direction": str(et or event.get("direction") or "analytic"),
                    "event_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(ts))),
                })
            except Exception as e:
                logger.debug(f"Analytic event persist error: {e}")


    def _generate_and_save_rollup(self, cam_id: str, ctx: Dict[str, Any], current_time: float):
        if ctx["tripwires"]:
            current_in = sum(tw.in_count for tw in ctx["tripwires"])
            current_out = sum(tw.out_count for tw in ctx["tripwires"])
            delta_in = current_in - ctx["last_in_count"]
            delta_out = current_out - ctx["last_out_count"]
            ctx["last_in_count"] = current_in
            ctx["last_out_count"] = current_out
            # People on floor now (= YOLO HUD), not tripwire IN−OUT net (looping demos).
            current_occupancy = len(ctx.get("current_active_tracks", []))
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
        if ctx["queues"]:
            queue_metrics = [q.get_metrics() for q in ctx["queues"]]
            queue_len = max(m["queue_length"] for m in queue_metrics)
            avg_wait = max(m["avg_wait_seconds"] for m in queue_metrics)
            alert_active = int(any(m["alert_active"] for m in queue_metrics))

        # --- Enrichment-tier aggregates -------------------------------------
        # A camera context built before the enrichment tier existed (or by a test)
        # simply contributes zeros rather than failing the rollup.
        attention_metrics = ctx["attention"].snapshot() if ctx.get("attention") else {}
        group_metrics = ctx["groups"].snapshot() if ctx.get("groups") else {}
        demographics_metrics = ctx["demographics"].snapshot() if ctx.get("demographics") else {}

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
            "queue_alert_active": alert_active,
            "avg_attention_score": attention_metrics.get("avg_attention_score", 0.0),
            "facing_ratio": attention_metrics.get("facing_ratio", 0.0),
            "phone_usage_rate": attention_metrics.get("phone_usage_rate", 0.0),
            "engaged_ratio": attention_metrics.get("engaged_ratio", 0.0),
            "group_count": group_metrics.get("group_count", 0),
            "people_in_groups": group_metrics.get("people_in_companies", 0),
            "demographics_json": json.dumps(demographics_metrics),
            "loop_count": int(getattr(ctx.get("reader"), "loop_count", 0) or 0),
            "is_simulated": 1 if getattr(ctx.get("reader"), "is_file", False) else 0,
            "source_session_id": getattr(self, "source_session_id", "test-session"),
        }

        self.local_buffer.save_rollup(rollup)
        self._persist_product_interest(cam_id, ctx, current_time)
        ctx["last_rollup_time"] = current_time
        ctx["rollup_start_time"] = current_time

        logger.info(
            f"[{cam_id}] People Count: {current_occupancy} live | "
            f"New Shoppers: +{delta_in} | Unique (pass): {len(ctx['tracked_ids_today'])} | "
            f"Unique across passes: {int(ctx.get('unique_total_all_passes', 0) or 0)} | "
            f"Loop: {int(getattr(ctx.get('reader'), 'loop_count', 0) or 0)} | "
            f"Decode FPS: {getattr(ctx.get('reader'), 'fps_actual', 0.0)} | "
            f"Inference FPS: {ctx.get('processed_fps', 0.0)}"
        )
        if ctx.get("slow_ticks", 0):
            logger.info(
                f"[{cam_id}] Engagement: attention {attention_metrics.get('avg_attention_score', 0.0):.2f} | "
                f"facing {attention_metrics.get('facing_ratio', 0.0):.0%} | "
                f"on phone {attention_metrics.get('phone_usage_rate', 0.0):.0%} | "
                f"groups {group_metrics.get('group_count', 0)} "
                f"({group_metrics.get('people_in_companies', 0)} together) | "
                f"demographics sample {demographics_metrics.get('sample_size', 0)} "
                f"(k={demographics_metrics.get('k_anonymity', 10)})"
            )

    def _persist_product_interest(self, cam_id: str, ctx: Dict[str, Any], current_time: float):
        """Writes the per-category product interest rows for this rollup window."""
        if not ctx.get("products"):
            return
        snapshot = ctx["products"].snapshot()
        products = snapshot.get("products") or []
        if not products:
            return
        timestamp_start = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ctx["rollup_start_time"]))
        timestamp_end = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(current_time))
        for product in products:
            try:
                self.local_buffer.save_product_interest({
                    "store_id": self.store_id,
                    "device_id": self.device_id,
                    "camera_id": cam_id,
                    "category": product["category"],
                    "viewers": product["viewers"],
                    "detections": product["detections"],
                    "total_dwell_seconds": product["total_dwell_seconds"],
                    "avg_dwell_seconds": product["avg_dwell_seconds"],
                    "timestamp_start": timestamp_start,
                    "timestamp_end": timestamp_end,
                })
            except Exception as e:
                logger.error(f"Failed to persist product interest row: {e}")

    def stop(self):
        self.running = False
        logger.info("Stopping pipeline and saving state...")
        if self.rtmpose_refiner is not None:
            self.rtmpose_refiner.close()
        for ctx in self.camera_contexts.values():
            thread = ctx.get("slow_thread")
            if thread is not None and thread.is_alive():
                thread.join(timeout=1.0)
            display_thread = ctx.get("display_thread")
            ctx["reader"].stop()
            if display_thread is not None and display_thread.is_alive():
                display_thread.join(timeout=1.0)
        self.exporter.stop()
        logger.info("EdgePipeline cleanly terminated.")

def main():
    pipeline_cfg = os.environ.get("PIPELINE_CONFIG", "configs/pipeline.yaml")
    cameras_cfg = os.environ.get("CAMERAS_CONFIG", "configs/cameras.yaml")

    try:
        with open(pipeline_cfg, "r") as f:
            config = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        config = {}
    db_path = (config.get("storage") or {}).get("db_path", "data/storage/edgesight.db")
    store_id = (config.get("edge") or {}).get("store_id", "store_default")
    try:
        runtime_lock = acquire_runtime_lock(db_path, store_id=store_id)
    except RuntimeError as exc:
        logger.error("Refusing duplicate live edge process: %s", exc)
        return

    pipeline = EdgePipeline(pipeline_cfg, cameras_cfg)

    def handle_signal(sig, frame):
        logger.info("Received termination signal.")
        pipeline.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        pipeline.start()
    finally:
        runtime_lock.close()

if __name__ == "__main__":
    main()
