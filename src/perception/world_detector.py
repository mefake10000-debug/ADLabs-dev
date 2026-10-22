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
    """Detects retail product categories using an open-vocabulary (YOLO-World) model.

    The closed COCO detector the person pipeline uses knows about "person" and 79 other
    everyday objects. It does not know what a shop sells. An open-vocabulary detector
    takes the category list at runtime instead of baking it into the weights, so the
    same checkpoint serves a clothing store, a pharmacy or a electronics shop by
    changing the vocabulary in the config -- no retraining.

    This is what turns "12 people in the store" into "4 people browsing footwear and
    3 browsing bags".
    """

    def __init__(
        self,
        model: Any,
        vocabulary: Optional[List[str]] = None,
        conf_threshold: float = 0.30,
        device: str = "auto",
    ):
        self.model = model
        self.vocabulary = list(vocabulary or DEFAULT_PRODUCT_VOCABULARY)
        self.conf_threshold = conf_threshold
        self.device = device
        self._classes_set = False

    def _ensure_classes(self):
        if self._classes_set:
            return
        self.model.set_classes(self.vocabulary)
        self._classes_set = True
        logger.info(f"Open-vocabulary detector set to {len(self.vocabulary)} categories")

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
            return []

        if not results or len(results) == 0:
            return []

        out: List[Dict[str, Any]] = []
        boxes = results[0].boxes
        for i in range(len(boxes)):
            cls_idx = int(boxes[i].cls[0].item())
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
