import logging
import os
from typing import List, Dict, Any, Tuple

try:
    import numpy as np
except ImportError:
    np = None

try:
    import cv2
except ImportError:
    cv2 = None

logger = logging.getLogger(__name__)

class PersonDetector:
    """YOLO-based person detector with automatic device selection and offline fallback."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        conf_thresh: float = 0.50,
        iou_thresh: float = 0.45,
        min_height: float = 85.0,
        min_width: float = 30.0,
        min_aspect_ratio: float = 1.0,
        max_aspect_ratio: float = 4.2,
        min_area: float = 3000.0
    ):
        self.model_name = model_name
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.min_height = min_height
        self.min_width = min_width
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.min_area = min_area
        self.model = None
        self._hog = None
        self.device = self._select_device()
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
            logger.info("YOLO model successfully loaded.")
        except Exception as e:
            logger.warning(f"Could not initialize Ultralytics YOLO ({e}). Initializing fallback detector.")
            self.model = None

    def detect(self, frame: Any) -> List[Dict[str, Any]]:
        """Detect people in frame. Returns list of bounding boxes with confidence scores."""
        if self.model is None:
            return self._fallback_detect(frame)

        try:
            # Run inference targeting class 0 ('person' in COCO dataset)
            results = self.model.predict(
                source=frame,
                classes=[0],
                conf=self.conf_thresh,
                iou=self.iou_thresh,
                device=self.device,
                verbose=False
            )

            detections = []
            if results and len(results) > 0:
                boxes = results[0].boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0].item())
                    cls = int(box.cls[0].item())

                    w = x2 - x1
                    h = y2 - y1
                    area = w * h
                    aspect = h / max(1.0, w)

                    # Anthropometric and geometry filtering for CCTV person detection
                    if h < self.min_height or w < self.min_width:
                        continue
                    if area < self.min_area:
                        continue
                    if aspect < self.min_aspect_ratio or aspect > self.max_aspect_ratio:
                        continue

                    detections.append({
                        "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                        "confidence": round(conf, 3),
                        "class_id": cls
                    })
            return self._suppress_contained_duplicates(detections)
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []

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

    def _fallback_detect(self, frame: Any) -> List[Dict[str, Any]]:
        """Classical HOG+SVM person detector, used when the neural model (YOLO)
        cannot be loaded. Noticeably less accurate than YOLO -- particularly on
        small/distant/occluded figures -- but real detection is strictly better
        than silently returning zero people."""
        if cv2 is None:
            return []

        if self._hog is None:
            self._hog = cv2.HOGDescriptor()
            self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        try:
            rects, weights = self._hog.detectMultiScale(
                frame, winStride=(8, 8), padding=(8, 8), scale=1.05
            )
        except Exception as e:
            logger.error(f"Fallback HOG detection error: {e}")
            return []

        detections = []
        for (x, y, w, h), weight in zip(rects, weights):
            area = w * h
            aspect = h / max(1.0, w)

            if h < self.min_height or w < self.min_width:
                continue
            if area < self.min_area:
                continue
            if aspect < self.min_aspect_ratio or aspect > self.max_aspect_ratio:
                continue

            # HOG's SVM decision score isn't a probability; squash to (0, 1) for a
            # confidence-shaped value comparable in spirit to the YOLO path.
            confidence = float(1.0 / (1.0 + np.exp(-weight))) if np is not None else 0.5
            if confidence < self.conf_thresh:
                continue

            detections.append({
                "bbox": [round(float(x), 1), round(float(y), 1), round(float(x + w), 1), round(float(y + h), 1)],
                "confidence": round(confidence, 3),
                "class_id": 0
            })

        return self._suppress_contained_duplicates(detections)

