import logging
import os
from typing import List, Dict, Any, Optional

try:
    import numpy as np
except ImportError:
    np = None

from src.perception.detector_backend import (
    BACKEND_RFDETR,
    BACKEND_YOLO26,
    RFDETR_RESOLUTIONS,
    resolve_rfdetr_variant,
    resolve_rfdetr_weights,
)

logger = logging.getLogger(__name__)

# COCO person class id (shared by YOLO26 and RF-DETR COCO checkpoints).
_PERSON_CLASS_ID = 0


class PersonDetector:
    """Person detector with YOLO26 (default) or RF-DETR (Apache SOTA) backends.

    There is deliberately no lower-accuracy classical fallback: HOG+SVM recovered only
    ~7-14% of people on real shop footage (docs/tracking-benchmark.md). With
    require_model=True a model that cannot load is a startup error. Without it the
    detector returns no detections and logs an error.

    Both backends emit ``bbox`` as xyxy floats so ByteTrack / overlays stay unchanged.
    Parallel-box overlays (OVERLAY_BOX_STYLE) consume the same xyxy AABB.
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        conf_thresh: float = 0.50,
        iou_thresh: float = 0.45,
        min_height: float = 85.0,
        min_width: float = 30.0,
        min_aspect_ratio: float = 1.0,
        max_aspect_ratio: float = 4.2,
        min_area: float = 3000.0,
        require_model: bool = False,
        imgsz: int = 640,
        backend: str = BACKEND_YOLO26,
        rfdetr_variant: Optional[str] = None,
        rfdetr_weights: Optional[str] = None,
        pipeline_cfg: Optional[Dict[str, Any]] = None,
    ):
        self.backend = (backend or BACKEND_YOLO26).strip().lower()
        if self.backend not in (BACKEND_YOLO26, BACKEND_RFDETR):
            raise ValueError(f"Unknown detector backend '{backend}' (use yolo26|rfdetr)")

        self.model_name = model_name
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.min_height = min_height
        self.min_width = min_width
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.min_area = min_area
        # Ultralytics letterbox size. RF-DETR uses a fixed native resolution per variant.
        self.imgsz = int(imgsz) if imgsz else 640
        self.model = None
        self.require_model = require_model
        self._warned_no_model = False
        self.device = self._select_device()
        self.rfdetr_variant = (rfdetr_variant or resolve_rfdetr_variant(pipeline_cfg)).lower()
        self.rfdetr_weights = rfdetr_weights or resolve_rfdetr_weights(
            self.rfdetr_variant, pipeline_cfg
        )
        self._loaded = False

        if self.backend == BACKEND_RFDETR:
            self._init_rfdetr()
        else:
            self._init_model()

    def _select_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon GPU acceleration
        except Exception:
            # torch may be absent, or present but broken (e.g. a native DLL/.so
            # failing to load) -- either way, fall back to CPU rather than crash.
            pass
        return "cpu"

    def _init_model(self):
        try:
            from ultralytics import YOLO
            # Models directory can be passed in pipeline configs
            logger.info(f"Loading YOLO model '{self.model_name}' on device '{self.device}'...")
            self.model = YOLO(self.model_name)
            self._loaded = True
            logger.info("YOLO model successfully loaded.")
        except Exception as e:
            self.model = None
            self._loaded = False
            if self.require_model:
                raise RuntimeError(
                    f"Could not load YOLO model '{self.model_name}': {e}. Refusing to run without a working "
                    f"detector (set perception.require_model: false only for development)."
                ) from e
            logger.error(f"Could not initialize Ultralytics YOLO ({e}). This detector will return NO detections.")

    def _init_rfdetr(self):
        """Load Roboflow RF-DETR Nano/Small (Apache-2.0). XL/2XL PML Plus is not used."""
        try:
            from rfdetr import RFDETRNano, RFDETRSmall
        except Exception as e:
            self.model = None
            self._loaded = False
            msg = (
                f"rfdetr package unavailable ({e}). Install with `pip install 'rfdetr>=1.3,<2'` "
                f"(Python>=3.10). DETECTOR_BACKEND=rfdetr requires the package."
            )
            if self.require_model:
                raise RuntimeError(msg) from e
            logger.error(msg)
            return

        cls = RFDETRNano if self.rfdetr_variant == "nano" else RFDETRSmall
        native = RFDETR_RESOLUTIONS.get(self.rfdetr_variant, 384)
        self.imgsz = native  # informational for live JSON / stack
        # Prefer pack / RF_HOME path as the model display name.
        self.model_name = self.rfdetr_weights or f"rf-detr-{self.rfdetr_variant}.pth"

        try:
            logger.info(
                "Loading RF-DETR-%s (%s) on device '%s' (Apache-2.0 SOTA path)...",
                self.rfdetr_variant.upper(),
                self.model_name,
                self.device,
            )
            # Device is typically picked by torch inside rfdetr; we still log resolved preference.
            self.model = cls(pretrain_weights=self.rfdetr_weights)
            # Optional in-place optimize (rfdetr.inference). Off by default — compile is slow
            # on first call; set RFDETR_OPTIMIZE=1 on CUDA/MPS quality hosts.
            if (
                os.environ.get("RFDETR_OPTIMIZE", "0").strip().lower() in ("1", "true", "yes", "on")
                and self.device in ("cuda", "mps")
                and hasattr(self.model, "inference")
            ):
                try:
                    self.model.inference(compile=False, inplace=True)
                except Exception as opt_err:  # noqa: BLE001
                    logger.warning("RF-DETR inference() optimize skipped: %s", opt_err)
            self._loaded = True
            logger.info("RF-DETR model successfully loaded.")
        except Exception as e:
            self.model = None
            self._loaded = False
            if self.require_model:
                raise RuntimeError(
                    f"Could not load RF-DETR '{self.rfdetr_weights}': {e}. "
                    f"Run `python3 scripts/download_pack_models_phase2.py --download --only rfdetr-nano` "
                    f"or let rfdetr auto-fetch into RF_HOME."
                ) from e
            logger.error("Could not initialize RF-DETR (%s). This detector will return NO detections.", e)

    @property
    def is_loaded(self) -> bool:
        return bool(self._loaded and self.model is not None)

    def detect(self, frame: Any) -> List[Dict[str, Any]]:
        """Detect people in frame. Returns list of bounding boxes with confidence scores."""
        if self.model is None:
            if not self._warned_no_model:
                logger.error("PersonDetector has no model loaded; returning no detections.")
                self._warned_no_model = True
            return []

        if self.backend == BACKEND_RFDETR:
            return self._detect_rfdetr(frame)
        return self._detect_yolo(frame)

    def _detect_yolo(self, frame: Any) -> List[Dict[str, Any]]:
        try:
            # Run inference targeting class 0 ('person' in COCO dataset)
            results = self.model.predict(
                source=frame,
                classes=[_PERSON_CLASS_ID],
                conf=self.conf_thresh,
                iou=self.iou_thresh,
                device=self.device,
                imgsz=self.imgsz,
                verbose=False
            )

            detections = []
            if results and len(results) > 0:
                boxes = results[0].boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0].item())
                    cls = int(box.cls[0].item())
                    det = self._filter_box(x1, y1, x2, y2, conf, cls)
                    if det:
                        detections.append(det)
            return self._suppress_contained_duplicates(detections)
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []

    def _detect_rfdetr(self, frame: Any) -> List[Dict[str, Any]]:
        """RF-DETR predict → xyxy person boxes (supervision.Detections)."""
        try:
            # rfdetr accepts numpy RGB or path; OpenCV frames are BGR.
            src = frame
            if np is not None and hasattr(frame, "shape") and len(getattr(frame, "shape", ())) == 3:
                # Assume BGR from cv2; convert to RGB for the ViT backbone.
                src = frame[:, :, ::-1].copy()

            dets = self.model.predict(src, threshold=float(self.conf_thresh))
            detections: List[Dict[str, Any]] = []
            if dets is None or getattr(dets, "xyxy", None) is None:
                return []

            xyxy = dets.xyxy
            confs = getattr(dets, "confidence", None)
            class_ids = getattr(dets, "class_id", None)
            n = len(xyxy)
            for i in range(n):
                cls = int(class_ids[i]) if class_ids is not None else _PERSON_CLASS_ID
                if cls != _PERSON_CLASS_ID:
                    continue
                x1, y1, x2, y2 = [float(v) for v in xyxy[i]]
                conf = float(confs[i]) if confs is not None else float(self.conf_thresh)
                det = self._filter_box(x1, y1, x2, y2, conf, cls)
                if det:
                    detections.append(det)
            return self._suppress_contained_duplicates(detections)
        except Exception as e:
            logger.error(f"RF-DETR detection error: {e}")
            return []

    def _filter_box(
        self, x1: float, y1: float, x2: float, y2: float, conf: float, cls: int
    ) -> Optional[Dict[str, Any]]:
        w = x2 - x1
        h = y2 - y1
        area = w * h
        aspect = h / max(1.0, w)

        # Anthropometric and geometry filtering for CCTV person detection
        if h < self.min_height or w < self.min_width:
            return None
        if area < self.min_area:
            return None
        if aspect < self.min_aspect_ratio or aspect > self.max_aspect_ratio:
            return None

        return {
            "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            "confidence": round(conf, 3),
            "class_id": cls,
        }

    @staticmethod
    def _suppress_contained_duplicates(detections: List[Dict[str, Any]], containment_threshold: float = 0.65) -> List[Dict[str, Any]]:
        """Suppresses nested part-vs-whole duplicate boxes (e.g. upper body or jacket detected separately from full body)."""
        if len(detections) <= 1:
            return detections

        # Sort by box area descending (larger full-body boxes evaluated first)
        sorted_dets = sorted(detections, key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]), reverse=True)
        keep = []

        for det in sorted_dets:
            bA = det["bbox"]
            areaA = (bA[2] - bA[0]) * (bA[3] - bA[1])
            is_contained = False

            for kept in keep:
                bB = kept["bbox"]
                inter_x1 = max(bA[0], bB[0])
                inter_y1 = max(bA[1], bB[1])
                inter_x2 = min(bA[2], bB[2])
                inter_y2 = min(bA[3], bB[3])

                if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                    if inter_area / max(1.0, areaA) >= containment_threshold:
                        is_contained = True
                        break

            if not is_contained:
                keep.append(det)

        return keep
