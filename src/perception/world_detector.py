import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Retail product vocabulary for open-vocabulary detection. This is deliberately a
# short list of *categories a shopper interacts with*, not a catalogue of SKUs: the
# model answers "is anyone near a shoe / bag / garment?", which is the question a
# merchandising team actually asks of a store camera. A store-specific vocabulary can
# be supplied via configs/pipeline.yaml without touching code.
DEFAULT_PRODUCT_VOCABULARY = [
    "shoe",
    "handbag",
    "backpack",
    "suitcase",
    "shirt",
    "dress",
    "jacket",
    "hat",
    "watch",
    "eyeglasses",
    "phone",
    "bottle",
    "shopping cart",
    "umbrella",
]


class OpenVocabProductDetector:
    """Detects retail product categories using an open-vocabulary model.

    Supports YOLO-World (``set_classes`` + CLIP text encoder via ``weights/clip``)
    and YOLOE prompt-free (``yoloe-*-seg-pf``) where CLIP is unavailable: built-in
    names are filtered down to the configured vocabulary by substring match.

    Categories are merchandising prompts — **not** POS / closed-set grocery SKUs.
    """

    def __init__(
        self,
        model: Any,
        vocabulary: Optional[List[str]] = None,
        conf_threshold: float = 0.30,
        device: str = "auto",
        mode: str = "auto",
    ):
        self.model = model
        self.vocabulary = list(vocabulary or DEFAULT_PRODUCT_VOCABULARY)
        self.conf_threshold = conf_threshold
        self.device = device
        self._classes_set = False
        self._prompt_free = False
        self._mode = (mode or "auto").lower()
        # Detect YOLOE / prompt-free early so we never call set_classes (needs CLIP).
        model_name = str(getattr(model, "__class__", type(model)).__name__).lower()
        task = str(getattr(model, "task", "") or "").lower()
        if self._mode in ("yoloe", "prompt_free") or "yoloe" in model_name or task == "segment":
            # Only force prompt-free when it looks like YOLOE; YOLO-World stays class-set.
            if self._mode in ("yoloe", "prompt_free") or "yoloe" in model_name:
                self._prompt_free = True
                logger.info(
                    "Open-vocab detector using YOLOE prompt-free path "
                    "(filter %d vocabulary terms against built-in names)",
                    len(self.vocabulary),
                )

    def _ensure_classes(self):
        if self._classes_set or self._prompt_free:
            return
        # Prefer openai-clip from requirements-edge.txt. Ultralytics otherwise retries
        # `pip install git+CLIP` (needs git, kills Docker CPU FPS under EDGE_PERF_MODE=fast).
        try:
            import clip  # noqa: F401
        except ImportError:
            logger.warning(
                "openai-clip missing — using prompt-free name filter "
                "(keep products disabled in fast mode; rebuild edge image to bake openai-clip)"
            )
            self._prompt_free = True
            self._classes_set = True
            return
        try:
            self.model.set_classes(self.vocabulary)
            self._classes_set = True
            logger.info(f"Open-vocabulary detector set to {len(self.vocabulary)} categories")
        except Exception as e:
            # YOLOE / other set_classes failures — fall back to prompt-free name filtering.
            logger.warning(
                "set_classes failed (%s); falling back to prompt-free name filter", e
            )
            self._prompt_free = True
            self._classes_set = True

    @staticmethod
    def _map_prompt_free_label(raw_name: str, vocabulary: List[str]) -> Optional[str]:
        """Map a YOLOE built-in class name onto our short retail vocabulary."""
        raw = (raw_name or "").strip().lower()
        if not raw:
            return None
        # Exact / contained matches prefer the configured vocab term.
        for term in vocabulary:
            t = term.lower()
            if raw == t or t in raw or raw in t:
                return term
        return None

    def detect(self, frame: Any) -> List[Dict[str, Any]]:
        """Returns product detections: bbox, confidence and the category label."""
        if self.model is None:
            return []
        try:
            self._ensure_classes()
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                iou=0.5,
                device=self.device,
                verbose=False,
            )
        except Exception as e:
            logger.error(f"Open-vocabulary inference error: {e}")
            # Stop retrying every slow-tier tick (CLIP autoinstall loops).
            self.model = None
            return []

        if not results or len(results) == 0:
            return []

        names = getattr(self.model, "names", None) or {}
        out: List[Dict[str, Any]] = []
        boxes = results[0].boxes
        for i in range(len(boxes)):
            cls_idx = int(boxes[i].cls[0].item())
            if self._prompt_free:
                raw = names.get(cls_idx, "") if isinstance(names, dict) else str(cls_idx)
                label = self._map_prompt_free_label(str(raw), self.vocabulary)
                if not label:
                    continue
            else:
                label = (
                    self.vocabulary[cls_idx]
                    if 0 <= cls_idx < len(self.vocabulary)
                    else f"class_{cls_idx}"
                )
            out.append({
                "bbox": [round(v, 1) for v in boxes[i].xyxy[0].tolist()],
                "confidence": round(float(boxes[i].conf[0].item()), 3),
                "class_id": cls_idx,
                "label": label,
            })
        return out


def filter_out_persons(
    detections: List[Dict[str, Any]],
    person_boxes: List[List[float]],
    max_overlap: float = 0.5,
) -> List[Dict[str, Any]]:
    """Drops product detections that are really a person wearing the product.

    An open-vocabulary model asked for "jacket" or "dress" will happily box the
    shopper wearing one. Counting that as a product would inflate the merchandising
    numbers with the people in the store, so a detection whose box overlaps a tracked
    person by more than `max_overlap` is discarded.

    Genuine apparel on a display stand is not overlapping a person, so it survives.
    """
    if not person_boxes:
        return detections

    kept: List[Dict[str, Any]] = []
    for det in detections:
        dx1, dy1, dx2, dy2 = det["bbox"]
        det_area = max(0.0, dx2 - dx1) * max(0.0, dy2 - dy1)
        worst = 0.0
        for px1, py1, px2, py2 in person_boxes:
            ix1, iy1 = max(dx1, px1), max(dy1, py1)
            ix2, iy2 = min(dx2, px2), min(dy2, py2)
            inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
            if inter <= 0:
                continue
            person_area = max(0.0, px2 - px1) * max(0.0, py2 - py1)
            union = det_area + person_area - inter
            iou = inter / union if union > 0 else 0.0
            worst = max(worst, iou)
        if worst <= max_overlap:
            kept.append(det)
    return kept
