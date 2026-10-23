import os
import sys
import time
import json
import signal
import yaml
import logging
import threading
from typing import Dict, List, Any, Optional

from src.ingestion.stream_reader import StreamReader
from src.perception.detector import PersonDetector
from src.perception.tracker import SimpleByteTracker, tracker_params_for_infer_gap
from src.perception.performance import limit_cameras, resolve_performance
from src.perception.detector_backend import BACKEND_RFDETR, backend_label
from src.perception.registry import ModelRegistry, ModelSpec, select_device, TIER_FAST, TIER_SLOW
from src.perception.model_stack import demographics_env_enabled
from src.perception.pose_estimator import PoseEstimator, match_pose_to_track
from src.perception.rtmpose_estimator import RTMPoseFootEstimator, resolve_rtmpose_onnx
from src.analytics.pose_fall_candidate import status as pose_fall_status
from src.analytics.shelf_gap_geometry import snapshot as shelf_gap_snapshot
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
from src.analytics.journey import build_journey_block
from src.analytics.staff_response import StaffQueueResponseTracker, build_staff_block
from src.storage.local_buffer import LocalBuffer
from src.telemetry.exporter import TelemetryExporter
from src.telemetry.health import HealthMonitor
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

        # Performance preset (EDGE_PERF_MODE / performance.mode). Balanced is the
        # Docker Mac ARM demo default — see docs/live-fps.md.
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
            or "yolov8n.pt"
        )
        conf_thresh = p_cfg.get("confidence_threshold", 0.50)
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
        )

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
        # Enrichment tier is EXPLICIT: fast/balanced force it off; quality keeps the
        # models.* yaml gating truthful (no silent re-enable). EDGE_ENRICHMENT overrides.
        _env_enrichment = os.environ.get("EDGE_ENRICHMENT")
        if _env_enrichment is not None:
            self.models_enabled = _env_enrichment not in ("", "0", "false", "False")
            logger.info(
                f"EDGE_ENRICHMENT={_env_enrichment} env override — enrichment "
                f"{'ON' if self.models_enabled else 'OFF'}"
            )
        elif self.perf_mode in ("fast", "balanced"):
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
        self.face_detector = None
        self.age_gender = None
        self.head_pose = None
        self.world_detector = None
        self.model_errors: Dict[str, str] = {}

        if self.models_enabled:
            self._init_enrichment_models()
        self._init_rtmpose()

        reid_cfg = (self.models_cfg.get("reid") or {}) if getattr(self, "models_cfg", None) is not None else {}
        # Fast/balanced keep ReID off; quality still requires models.reid.enabled: true.
        reid_enabled = bool(reid_cfg.get("enabled", False)) and self.perf_mode == "quality"
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

        (reproduced by scripts/check_mps_concurrency.py). So when the fast tier owns
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
        if not demographics_env_enabled():
            demo_cfg["enabled"] = False
            self.models_cfg["demographics"] = demo_cfg
            logger.info(
                "Demographics model gated off (ENABLE_DEMOGRAPHICS=%s). "
                "Set ENABLE_DEMOGRAPHICS=1 and DEMOGRAPHICS_DPIA_OK=1 after DPIA + k≥10 wiring.",
                os.environ.get("ENABLE_DEMOGRAPHICS", "0"),
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
        if demo_cfg.get("enabled", True):
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

        if demo_cfg.get("enabled", True):
            session = self.registry.get("demographics")
            if session is not None:
                self.age_gender = AgeGenderEstimator(
                    session,
                    min_face_px=float(face_cfg.get("min_face_px", 30)),
                )
            else:
                self.model_errors["demographics"] = self.registry.error("demographics") or "unavailable"

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
        if self.rtmpose is None or not tracks or frame is None:
            return
        every = int(getattr(self, "rtmpose_every_n", 4) or 4)
        tick = int(ctx.get("rtmpose_tick", 0) or 0) + 1
        ctx["rtmpose_tick"] = tick
        if tick % every != 0:
            return
        try:
            poses = self.rtmpose.estimate_on_bboxes(frame, [t.bbox for t in tracks])
        except Exception as e:  # noqa: BLE001
            logger.debug("RTMPose pass failed: %s", e)
            return
        for track, pose in zip(tracks, poses):
            foot = pose.get("foot_point")
            if foot:
                track.set_pose(
                    foot=(float(foot[0]), float(foot[1])),
                    keypoints=pose.get("keypoints"),
                    keypoints_xy=pose.get("keypoints_xy"),
                )

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
                staff_zones.append(sz)
            elif ztype == "queue":
                queues.append(QueueAnalyzer(
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
                ))
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
        }, sort_keys=True)

    def _make_tracker(self) -> SimpleByteTracker:
        """ByteTrack knobs aligned with ``infer_every_n`` (skipped frames break IDs)."""
        t_cfg = self.pipeline_cfg.get("tracking", {}) or {}
        scaled = tracker_params_for_infer_gap(
            int(getattr(self, "infer_every_n", 1) or 1),
            track_buffer=int(t_cfg.get("track_buffer", 45)),
            match_thresh=float(t_cfg.get("match_thresh", 0.45)),
            min_hits=int(t_cfg.get("min_hits", 4)),
            track_thresh=float(t_cfg.get("track_thresh", 0.5)),
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
        }

    def _init_cameras(self):
        cams = list(self.cameras_cfg.get("cameras", []))
        limited = limit_cameras(cams, self.perf.get("max_cameras"))
        if len(limited) < len(cams):
            logger.info(
                "EDGE_MAX_CAMERAS / performance.max_cameras=%s — using %s of %s cameras for FPS budget",
                self.perf.get("max_cameras"),
                len(limited),
                len(cams),
            )
        for cam in limited:
            self.camera_contexts[cam["id"]] = self._build_camera_context(cam)
            logger.info(f"Initialized pipeline for camera: {cam.get('name', cam['id'])} ({cam['id']})")

    def start(self):
        self.running = True
        self.exporter.start()

        import threading as _threading
        reg = _threading.Thread(target=self._device_registration_loop, name="DeviceRegister", daemon=True)
        reg.start()

        for ctx in self.camera_contexts.values():
            ctx["reader"].start()
            self._start_slow_tier(ctx)

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
                    ctx["frames_processed"] += 1
                    ctx["last_capture_ts_utc"] = frame_time
                    ctx["last_capture_ts_mono"] = getattr(stamp, "mono", frame_time)

                    # Display vs analytics cadence: decode every frame for a smooth MJPEG
                    # path; run detect+track only every infer_every_n frames.
                    do_infer = (ctx["frames_processed"] % self.infer_every_n) == 0

                    if self.models_enabled:
                        # Publish the frame for the enrichment tier. The slow worker runs
                        # in its own thread, so it gets its own copy: the debug overlay
                        # draws on this buffer in place and a half-drawn frame would be
                        # nonsense to a face model.
                        with ctx["frame_lock"]:
                            ctx["latest_frame"] = (frame_idx, frame_time, frame.copy())

                    if do_infer:
                        # Inference throughput (frames actually run through detect+track).
                        ctx["fps_window_frames"] += 1
                        window = time.time() - ctx["fps_window_start"]
                        if window >= 2.0:
                            ctx["processed_fps"] = round(ctx["fps_window_frames"] / window, 1)
                            ctx["fps_window_start"] = time.time()
                            ctx["fps_window_frames"] = 0

                        # 1. Perception — Ultralytics YOLO people (+ COCO store objects for overlay)
                        if hasattr(self.detector, "detect_frame"):
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
                        # Staff polygons first — sticky tags, then customer-only analytics
                        for staff_zone in ctx.get("staff_zones", []):
                            staff_zone.update(active_tracks, frame_time)
                            for tid, entered in staff_zone.active_tracks_in_zone.items():
                                if frame_time - entered >= self.staff_min_seconds:
                                    ctx["staff_ids"].add(tid)
                        customers = [t for t in active_tracks if t.track_id not in ctx["staff_ids"]]
                        early_customers = [
                            t for t in early_tracks if t.track_id not in ctx["staff_ids"]
                        ]
                        for t in customers:
                            t.dwell_s = 0.0
                            t.zone_id = None
                        ctx["current_active_tracks"] = customers
                        ctx["last_overlay_tracks"] = active_tracks
                        ctx["staff_visible"] = len(active_tracks) - len(customers)
                        # Sample footage replays: on the loop boundary archive this pass's
                        # uniques and reset per-pass counters (looping otherwise inflates).
                        _reader = ctx.get("reader")
                        _loops = int(getattr(_reader, "loop_count", 0) or 0)
                        if _loops != ctx.get("reader_loop_seen", 0):
                            self._reset_sim_pass(cam_id, ctx, _loops)
                        ctx["tracked_ids_today"].update(t.track_id for t in active_tracks)

                        # 3. Spatial Analytics (customers only)
                        crossing_events: List[Dict[str, Any]] = []
                        for tw in ctx["tripwires"]:
                            crossing_events.extend(tw.update(early_customers, frame_time))
                        if crossing_events:
                            self._persist_crossing_events(cam_id, crossing_events)
                            recent = ctx.setdefault("recent_trip_in", {})
                            for ev in crossing_events:
                                direction = str(ev.get("direction", "")).lower()
                                if direction in ("in", "trip_in", "enter"):
                                    tid = ev.get("track_id")
                                    if tid is not None:
                                        recent[int(tid)] = float(ev.get("timestamp") or frame_time)
                            cutoff = frame_time - 120.0
                            for tid in list(recent.keys()):
                                if recent[tid] < cutoff:
                                    del recent[tid]

                        for zone in ctx["zones"]:
                            zone.update(customers, frame_time)

                        staff_on_post = int(ctx.get("staff_visible", 0) or 0)
                        analytic_events: List[Dict[str, Any]] = []
                        for q in ctx["queues"]:
                            try:
                                analytic_events.extend(
                                    q.update(customers, frame_time, staff_on_post=staff_on_post) or []
                                )
                            except TypeError:
                                q.update(customers, frame_time)

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
                            try:
                                floor.set_frame_size(float(frame.shape[1]), float(frame.shape[0]))
                            except Exception:
                                pass
                            floor.update(customers, list(ctx.get("zones") or []), frame_time)

                        safety = ctx.get("safety")
                        if safety is not None:
                            safety.update(
                                customers,
                                list(ctx.get("zones") or []),
                                frame_time,
                                cam_id,
                            )

                        if analytic_events and hasattr(self, "_persist_analytic_events"):
                            self._persist_analytic_events(cam_id, analytic_events)

                        if ctx.get("heatmap") is None:
                            ctx["heatmap"] = Heatmap(frame.shape[1], frame.shape[0])
                        ctx["heatmap"].add(customers, frame_time)
                        if cv2 is not None and frame_time - ctx.get("last_heatmap_write", 0.0) >= self.heatmap_write_seconds:
                            self._write_heatmap(cam_id, ctx, frame, frame_time)
                    else:
                        active_tracks = list(ctx.get("last_overlay_tracks") or [])

                    # 4. Display stream — refresh MJPEG from latest decode + last tracks
                    # even when this frame skipped inference (smoother portal video).
                    if cv2 is not None and (ctx["frames_processed"] % self.display_every_n) == 0:
                        try:
                            draw_kwargs = dict(
                                frame=frame,
                                tracks=active_tracks,
                                tripwires=ctx["tripwires"],
                                zones=ctx["zones"],
                                queues=ctx["queues"],
                                camera_name=ctx["name"],
                                fps=ctx["reader"].fps_actual,
                                infer_fps=ctx["processed_fps"],
                            )
                            try:
                                annotated = DebugOverlay.draw_pipeline(
                                    **draw_kwargs,
                                    staff_zones=ctx.get("staff_zones", []),
                                    staff_ids=ctx.get("staff_ids", set()),
                                    objects=list(ctx.get("last_overlay_objects") or []),
                                )
                            except TypeError:
                                annotated = DebugOverlay.draw_pipeline(**draw_kwargs)
                            frame_path = os.path.join(self.frames_dir, f"{cam_id}.jpg")
                            tmp_path = os.path.join(self.frames_dir, f"{cam_id}.tmp.jpg")
                            cv2.imwrite(tmp_path, annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                            os.replace(tmp_path, frame_path)
                            ctx["display_window_frames"] = int(ctx.get("display_window_frames", 0) or 0) + 1
                            dwin = time.time() - float(ctx.get("display_window_start", time.time()))
                            if dwin >= 2.0:
                                ctx["display_fps"] = round(ctx["display_window_frames"] / dwin, 1)
                                ctx["display_window_start"] = time.time()
                                ctx["display_window_frames"] = 0
                        except Exception as e:
                            logger.debug(f"Frame export error for {cam_id}: {e}")

                    # 4b. Frame-synced live JSON (portal KPIs tick with the YOLO overlay)
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

    # --------------------------------------------------------- enrichment tier
    def _start_slow_tier(self, ctx: Dict[str, Any]):
        """Starts the enrichment worker for one camera.

        The enrichment models (pose, face, demographics, products) cost far more per
        frame than person detection. Running them inline would cut the throughput of
        the core counters, so they get their own thread and their own frame copy.
        The fast tier therefore keeps its latency while the enrichment tier catches up
        on its own cadence.
        """
        if not getattr(self, "models_enabled", False):
            return
        if self.pose_estimator is None and self.face_detector is None \
                and self.age_gender is None and self.world_detector is None:
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
                frame_idx, frame_time, frame = latest
                # Honour the configured cadence. The frame index counts decoded frames,
                # so this is "every N video frames" regardless of how fast inference runs.
                if frame_idx - ctx["last_slow_frame_idx"] < interval:
                    time.sleep(0.01)
                    continue
                ctx["last_slow_frame_idx"] = frame_idx
                try:
                    self._process_slow_tier(cam_id, ctx, frame_time, frame)
                    ctx["slow_ticks"] += 1
                except Exception as e:
                    logger.error(f"Enrichment pass failed on {cam_id}: {e}", exc_info=True)

        thread = threading.Thread(target=_worker, name=f"Enrichment-{cam_id}", daemon=True)
        ctx["slow_thread"] = thread
        thread.start()
        logger.info(f"Enrichment tier started for camera '{cam_id}' (every {interval} frames).")

    def _process_slow_tier(self, cam_id: str, ctx: Dict[str, Any], frame_time: float, frame: Any):
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

        # --- 1. Pose: what the body is doing ---------------------------------
        pose_by_track: Dict[int, Dict[str, Any]] = {}
        if self.pose_estimator is not None:
            iou_min = float(pose_cfg.get("match_iou", 0.30))
            for pose in self.pose_estimator.estimate(frame):
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
        faces = self.face_detector.detect(frame) if self.face_detector is not None else []
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
        if self.face_detector is not None and bool(face_cfg.get("upscale_crops", True)):
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
        if self.age_gender is not None and face_by_track:
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
            crops = []
            for _track_id, face in selected:
                crop = None
                if align:
                    crop = align_face(frame, face)
                if crop is None:
                    crop = crop_face(frame, face)
                crops.append(crop)
            results = self.age_gender.predict_batch(crops)
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
        if self.world_detector is not None:
            detections = self.world_detector.detect(frame)
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
        self._sample_soft_reid(cam_id, ctx, tracks, frame, frame_time)

        # --- 7. Housekeeping -------------------------------------------------
        active_ids = [t.track_id for t in tracks]
        demographics.prune(active_ids, frame_time)
        attention.prune(active_ids)
        ctx["groups"].prune(active_ids)
        ctx["products"].prune(active_ids)


    def _sample_soft_reid(self, cam_id, ctx, tracks, frame, frame_time):
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
            ))

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
        cams_list = limit_cameras(cams_list, self.perf.get("max_cameras"))
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
                logger.info(f"Camera {cam_id} added from config.")
                continue

            if cam.get("source", "") != ctx["source"] or cam.get("fps_target", 15) != ctx["fps_target"]:
                self._generate_and_save_rollup(cam_id, ctx, time.time())
                ctx["reader"].stop()
                self.camera_contexts[cam_id] = self._build_camera_context(cam)
                if self.running:
                    self.camera_contexts[cam_id]["reader"].start()
                    self._start_slow_tier(self.camera_contexts[cam_id])
                logger.info(f"Camera {cam_id} source changed: {ctx['source']} -> {cam.get('source', '')}")
                continue

            ctx["name"] = cam.get("name", cam_id)
            if self._calibration_signature(cam) != ctx["calibration_sig"]:
                # Flush the old counters first, then reset the delta baselines: the new
                # Tripwire objects start at zero, so a stale last_in_count would make the
                # next rollup's delta negative.
                self._generate_and_save_rollup(cam_id, ctx, time.time())
                ctx["tripwires"], ctx["zones"], ctx["queues"], ctx["staff_zones"], ctx["glass_rois"] = self._build_analytics(cam)
                ctx["calibration_sig"] = self._calibration_signature(cam)
                ctx["last_in_count"] = 0
                ctx["last_out_count"] = 0
                ctx["staff_ids"] = set()
                logger.info(
                    f"Hot-reloaded {len(ctx['tripwires'])} tripwires and "
                    f"{len(ctx['zones']) + len(ctx['queues']) + len(ctx.get('staff_zones', []))} zones for {cam_id}"
                )

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
        if ctx.get("products"):
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
        if not products_top:
            try:
                products_top = self.local_buffer.get_recent_products_top(cam_id, limit=8) or None
            except Exception:
                products_top = None
        if products_top is not None and len(products_top) == 0:
            products_top = None
        reid_status = self.reid_extractor.status() if getattr(self, "reid_extractor", None) else {}

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
            "shelf_gap": shelf_gap_snapshot([]),
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
                "imgsz": int(getattr(self.detector, "imgsz", 0) or 0) or None,
                "tracker": "bytetrack",
                "perf_mode": getattr(self, "perf_mode", "balanced"),
                "infer_every_n": int(getattr(self, "infer_every_n", 1) or 1),
                "overlay_box_style": resolve_overlay_box_style(),
                "enrichment": bool(getattr(self, "models_enabled", False)),
                "pose": bool(getattr(self, "rtmpose", None)) or bool(getattr(self, "pose_estimator", None)),
                "rtmpose": bool(getattr(self, "rtmpose", None)),
                "rtmpose_backend": getattr(getattr(self, "rtmpose", None), "backend", None),
                "face_boxes": bool(getattr(self, "face_detector", None)),
                "products": bool(getattr(self, "world_detector", None)) or bool(products_top),
                "demographics_enabled": demographics_env_enabled(),
                "face_identity": False,
                "stack_policy": "docs/model-stack-policy.md",
                "note": (
                    f"perf={getattr(self, 'perf_mode', 'balanced')}: "
                    f"backend={getattr(self.detector, 'backend', 'yolo26')}; "
                    f"overlay={resolve_overlay_box_style()}; "
                    "person detect+track+foot zones"
                    + ("; rtmpose on" if getattr(self, "rtmpose", None) else "; foot=bbox")
                    + ("; enrichment on" if getattr(self, "models_enabled", False) else "; enrichment off")
                    + ". Face boxes (if on) = k-anon age/gender only — no face ID. "
                    "Soft ReID session-scoped only. products_top = open-vocab categories, not POS SKUs. "
                    "MiVOLO demographics stay GATED."
                ),
            },
            "perf_mode": getattr(self, "perf_mode", "balanced"),
            "reid": {
                "active": bool(reid_status.get("active")),
                "backend": reid_status.get("backend"),
                "gallery_size": self.reid_gallery.size() if self.reid_gallery else 0,
                "session_scoped": True,
                "cross_cam_fusion": False,
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

    def _persist_analytic_events(self, cam_id: str, events: List[Dict[str, Any]]):
        """Persist additive queue episode events (join/leave) on the durable channel.

        Non-trip events reuse wire_id/direction columns (event name in direction) so
        existing exporters and UIs keep working; unknown values are ignored by old UIs.
        Transient per-frame thresholds (queue_wait_ms_reached) are skipped.
        """
        skip = {"queue_wait_ms_reached", "glass_stop_reached", "glass_roi_ping"}
        for event in events:
            et = event.get("event") or event.get("direction")
            if et in skip:
                continue
            tid = event.get("track_id")
            ts = event.get("timestamp") or time.time()
            try:
                self.local_buffer.save_event({
                    "store_id": self.store_id,
                    "device_id": self.device_id,
                    "camera_id": cam_id,
                    "wire_id": event.get("wire_id") or event.get("queue_id") or str(et or "analytic"),
                    "track_id": int(tid or 0),
                    "direction": str(et or event.get("direction") or "analytic"),
                    "event_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(ts))),
                })
            except Exception as e:
                logger.debug(f"Analytic event persist error: {e}")

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
            headers={"Content-Type": "application/json"},
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
        for ctx in self.camera_contexts.values():
            thread = ctx.get("slow_thread")
            if thread is not None and thread.is_alive():
                thread.join(timeout=1.0)
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

