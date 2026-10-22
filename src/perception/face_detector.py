import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# YuNet returns a 15-float row per face:
#   0-3   x, y, w, h  (top-left corner + size)
#   4-5   right eye
#   6-7   left eye
#   8-9   nose tip
#   10-11 right mouth corner
#   12-13 left mouth corner
#   14    score
FACE_STRIDE = 15


class FaceDetector:
    """Face detection with YuNet (OpenCV DNN), including 5 facial landmarks.

    YuNet is used rather than a heavier face network because it is a 232KB ONNX model
    that runs comfortably inside the edge pipeline's frame budget, and it ships the
    landmarks we need for head-pose estimation without a second model.

    Nothing here persists a face. The output is an in-memory box + landmark set that is
    consumed by the head-pose and demographic estimators and then discarded with the
    frame.
    """

    def __init__(
        self,
        model_path: str,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
        input_size: Tuple[int, int] = (320, 320),
    ):
        self.model_path = model_path
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.top_k = top_k
        self.input_size = input_size
        self._detector = None
        self._last_size = input_size

    def _ensure_detector(self):
        if self._detector is not None:
            return self._detector
        import cv2
        if not hasattr(cv2, "FaceDetectorYN"):
            raise RuntimeError(
                "opencv-python was built without FaceDetectorYN (YuNet). "
                "Install opencv-python (not opencv-python-headless) with DNN support."
            )
        self._detector = cv2.FaceDetectorYN.create(
            self.model_path,
            "",
            self.input_size,
            self.score_threshold,
            self.nms_threshold,
            self.top_k,
        )
        return self._detector

    def detect(self, frame: Any) -> List[Dict[str, Any]]:
        """Detects faces in a BGR frame. Returns boxes + landmarks in frame coordinates."""
        import cv2

        detector = self._ensure_detector()
        height, width = frame.shape[:2]
        if (width, height) != self._last_size:
            detector.setInputSize((width, height))
            self._last_size = (width, height)

        try:
            _retval, faces = detector.detect(frame)
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []

        if faces is None or len(faces) == 0:
            return []

        out: List[Dict[str, Any]] = []
        for row in faces:
            x, y, w, h = float(row[0]), float(row[1]), float(row[2]), float(row[3])
            score = float(row[14])
            # A zero-area box means the row is a padded/unused slot.
            if w <= 1 or h <= 1:
                continue
            out.append({
                "bbox": [round(x, 1), round(y, 1), round(x + w, 1), round(y + h, 1)],
                "width": round(w, 1),
                "height": round(h, 1),
                "score": round(score, 3),
                "landmarks": {
                    "right_eye": [round(float(row[4]), 1), round(float(row[5]), 1)],
                    "left_eye": [round(float(row[6]), 1), round(float(row[7]), 1)],
                    "nose": [round(float(row[8]), 1), round(float(row[9]), 1)],
                    "right_mouth": [round(float(row[10]), 1), round(float(row[11]), 1)],
                    "left_mouth": [round(float(row[12]), 1), round(float(row[13]), 1)],
                },
            })
        return out

    def detect_in_crop(self, frame: Any, crop: List[float]) -> List[Dict[str, Any]]:
        """Detects faces inside a crop and returns them in *frame* coordinates.

        Wide-angle store cameras put faces at 20-40px, which is at the edge of what
        YuNet can resolve. Running the same detector on an upscaled person crop
        recovers those faces; this path exists for that, and is used only when the
        frame-level pass did not produce a face for a tracked person.
        """
        import cv2

        x1, y1, x2, y2 = [int(v) for v in crop]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 16 or y2 - y1 < 16:
            return []

        patch = frame[y1:y2, x1:x2]
        scale = 2.0
        patch = cv2.resize(patch, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        detector = self._ensure_detector()
        ph, pw = patch.shape[:2]
        if (pw, ph) != self._last_size:
            detector.setInputSize((pw, ph))
            self._last_size = (pw, ph)
        try:
            _retval, faces = detector.detect(patch)
        except Exception as e:
            logger.error(f"Face detection (crop) error: {e}")
            return []

        if faces is None or len(faces) == 0:
            return []

        out: List[Dict[str, Any]] = []
        for row in faces:
            fx, fy, fw, fh = float(row[0]), float(row[1]), float(row[2]), float(row[3])
            score = float(row[14])
            if fw <= 1 or fh <= 1:
                continue
            out.append({
                "bbox": [
                    round(x1 + fx / scale, 1), round(y1 + fy / scale, 1),
                    round(x1 + (fx + fw) / scale, 1), round(y1 + (fy + fh) / scale, 1),
                ],
                "width": round(fw / scale, 1),
                "height": round(fh / scale, 1),
                "score": round(score, 3),
                "landmarks": {
                    "right_eye": [round(x1 + float(row[4]) / scale, 1), round(y1 + float(row[5]) / scale, 1)],
                    "left_eye": [round(x1 + float(row[6]) / scale, 1), round(y1 + float(row[7]) / scale, 1)],
                    "nose": [round(x1 + float(row[8]) / scale, 1), round(y1 + float(row[9]) / scale, 1)],
                    "right_mouth": [round(x1 + float(row[10]) / scale, 1), round(y1 + float(row[11]) / scale, 1)],
                    "left_mouth": [round(x1 + float(row[12]) / scale, 1), round(y1 + float(row[13]) / scale, 1)],
                },
            })
        return out


def face_inside_box(face: Dict[str, Any], box: List[float], min_overlap: float = 0.35) -> bool:
    """True when a detected face plausibly belongs to the person in `box`.

    Uses the face centre against the upper half of the body box, which is where a head
    must be. A centre-only test avoids failing on boxes that are slightly loose.
    """
    fx1, fy1, fx2, fy2 = face["bbox"]
    cx = (fx1 + fx2) / 2.0
    cy = (fy1 + fy2) / 2.0
    bx1, by1, bx2, by2 = box
    upper_limit = by1 + (by2 - by1) * 0.55
    return (bx1 <= cx <= bx2) and (by1 <= cy <= upper_limit)


def crop_face(frame: Any, face: Dict[str, Any], margin: float = 0.35) -> Any:
    """Crops a padded region around a face for attribute models.

    The margin matters: a demographic model trained on loosely cropped faces degrades
    sharply when the crop is tight to the eyes.
    """
    import cv2

    x1, y1, x2, y2 = face["bbox"]
    w = max(1.0, x2 - x1)
    h = max(1.0, y2 - y1)
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    half_w = w * (0.5 + margin)
    half_h = h * (0.5 + margin)
    fh, fw = frame.shape[:2]
    nx1 = max(0, int(cx - half_w))
    ny1 = max(0, int(cy - half_h))
    nx2 = min(fw, int(cx + half_w))
    ny2 = min(fh, int(cy + half_h))
    if nx2 - nx1 < 8 or ny2 - ny1 < 8:
        return None
    return frame[ny1:ny2, nx1:nx2]


# Canonical 5-point face template (right eye, left eye, nose, right mouth, left mouth)
# in a 224x224 canvas. This is the ArcFace/InsightFace reference template scaled up,
# and it is the geometry the age/gender model implicitly expects: UTKFace-style
# training sets are landmark-aligned to a canonical face, so a raw CCTV crop fed
# straight in is out of distribution.
_ARCFACE_TEMPLATE_112 = np.array([
    [38.2946, 51.6963],   # right eye
    [73.5318, 51.5014],   # left eye
    [56.0252, 71.7366],   # nose
    [41.5493, 92.3655],   # right mouth
    [70.7299, 92.2041],   # left mouth
], dtype=np.float32)


def align_face(frame: Any, face: Dict[str, Any], size: int = 224) -> Optional[Any]:
    """Warps a face onto the canonical 5-point template.

    Demographic models trained on aligned datasets (UTKFace, Adience) expect the
    eyes, nose and mouth at fixed positions. A wide-angle CCTV crop has the face
    at an arbitrary pose, size and position, so the model sees an out-of-distribution
    input and its outputs drift -- in testing, adults in store footage were being
    read as children.

    The similarity transform (rotation + uniform scale + translation) is estimated
    from the five YuNet landmarks, so the warp corrects head pose as well as
    position. It is not a full 3D pose correction: a profile face still warps into
    a distorted frontal. A landmark-quality check below rejects the hopeless cases.
    """
    import cv2

    landmarks = face.get("landmarks") or {}
    order = ("right_eye", "left_eye", "nose", "right_mouth", "left_mouth")
    src = []
    for name in order:
        lm = landmarks.get(name)
        if not lm:
            return None
        src.append([float(lm[0]), float(lm[1])])
    src_np = np.array(src, dtype=np.float32)

    # Reject geometrically implausible landmarks: an eye-to-eye distance that is a
    # large fraction of the face width means the detector returned a bad landmark
    # set, and warping on it would produce a worse crop than no crop at all.
    eye_dist = float(np.linalg.norm(src_np[0] - src_np[1]))
    face_w = max(1.0, face["bbox"][2] - face["bbox"][0])
    face_h = max(1.0, face["bbox"][3] - face["bbox"][1])
    if eye_dist < face_w * 0.20 or eye_dist > face_w * 0.85:
        return None
    mouth_mid = (src_np[3] + src_np[4]) / 2.0
    eye_mid = (src_np[0] + src_np[1]) / 2.0
    # Eye-to-mouth span as a fraction of face height. The canonical template puts
    # the eyes at 46% and the mouth at 82% of the canvas, so a frontal face lands
    # near 0.36. Values far outside that indicate a broken landmark set.
    eye_mouth_span = (mouth_mid[1] - eye_mid[1]) / max(1.0, face_h)
    if not (0.15 < eye_mouth_span < 0.65):
        return None

    template = _ARCFACE_TEMPLATE_112 * (size / 112.0)
    matrix, _ = cv2.estimateAffinePartial2D(
        src_np, template, method=cv2.LMEDS
    )
    if matrix is None:
        return None

    warped = cv2.warpAffine(
        frame,
        matrix,
        (size, size),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return warped
