import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# COCO-17 keypoint order used by the ultralytics pose models.
KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

KP = {name: i for i, name in enumerate(KEYPOINT_NAMES)}


class PoseEstimator:
    """Body-pose estimation on top of a YOLO pose checkpoint.

    The person detector already tells us where people are; pose tells us what they are
    *doing*, which is what turns footfall into retail behaviour:

      * `foot_point`   -- ground contact point, used for zone/tripwire geometry. The
                           bbox bottom is the cheapest proxy and is what the existing
                           pipeline uses; the ankle midpoint is measurably better, so
                           zone tests can use it when pose is available.
      * `phone_in_hand`-- a wrist raised to head height. Phone use is the single
                           biggest driver of low engagement, and it is invisible in
                           aggregate counters.
      * `carrying_bag` -- a hand below the hip and outside the torso line.
      * `posture`      -- standing vs seated/crouched, from the torso/leg ratio.
      * `head_point`   -- used to pair a detected face with a body.
    """

    def __init__(self, model: Any, conf_threshold: float = 0.30, device: str = "auto"):
        self.model = model
        self.conf_threshold = conf_threshold
        self.device = device

    def estimate(self, frame: Any) -> List[Dict[str, Any]]:
        """Returns one dict per detected person: bbox, keypoints and derived attributes."""
        if self.model is None:
            return []
        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                iou=0.5,
                device=self.device,
                verbose=False,
            )
        except Exception as e:
            logger.error(f"Pose inference error: {e}")
            return []

        if not results or len(results) == 0:
            return []

        out: List[Dict[str, Any]] = []
        result = results[0]
        boxes = result.boxes
        keypoints = getattr(result, "keypoints", None)
        if keypoints is None:
            return []

        kp_xy = keypoints.xy
        kp_conf = keypoints.conf
        # keypoints.xy is (N, K, 2) and keypoints.conf is (N, K); older exports can
        # return a (N, K) tuple where the second axis holds the confidence.
        if isinstance(kp_xy, (list, tuple)):
            kp_xy = kp_xy[0]
        if isinstance(kp_conf, (list, tuple)):
            kp_conf = kp_conf[0]

        for i in range(len(boxes)):
            xyxy = boxes[i].xyxy[0].tolist()
            conf = float(boxes[i].conf[0].item())
            pts = kp_xy[i]
            confs = kp_conf[i]

            person: Dict[str, Any] = {
                "bbox": [round(v, 1) for v in xyxy],
                "confidence": round(conf, 3),
                "keypoints": {},
                "keypoint_confidence": {},
                "foot_point": None,
                "head_point": None,
                "shoulder_width": 0.0,
                "torso_height": 0.0,
                "posture": "unknown",
                "phone_in_hand": False,
                "carrying_bag": False,
                "arms_raised": False,
                "visible_keypoints": 0,
            }

            valid: Dict[str, Any] = {}
            for k_name, k_idx in KP.items():
                if k_idx >= len(pts):
                    continue
                k_conf = float(confs[k_idx].item()) if confs is not None else 1.0
                if k_conf < 0.3:
                    continue
                x, y = float(pts[k_idx][0].item()), float(pts[k_idx][1].item())
                valid[k_name] = (x, y)
                person["keypoints"][k_name] = [round(x, 1), round(y, 1)]
                person["keypoint_confidence"][k_name] = round(k_conf, 3)

            person["visible_keypoints"] = len(valid)
            if not valid:
                continue

            self._derive_attributes(person, valid)
            out.append(person)

        return out

    @staticmethod
    def _derive_attributes(person: Dict[str, Any], kp: Dict[str, Any]):
        person.setdefault("phone_in_hand", False)
        person.setdefault("arms_raised", False)
        person.setdefault("carrying_bag", False)

        left_ankle = kp.get("left_ankle")
        right_ankle = kp.get("right_ankle")
        ankles = [a for a in (left_ankle, right_ankle) if a]
        if ankles:
            person["foot_point"] = [
                round(sum(a[0] for a in ankles) / len(ankles), 1),
                round(max(a[1] for a in ankles), 1),
            ]

        nose = kp.get("nose")
        if nose:
            person["head_point"] = [round(nose[0], 1), round(nose[1], 1)]

        left_sh = kp.get("left_shoulder")
        right_sh = kp.get("right_shoulder")
        shoulders = [s for s in (left_sh, right_sh) if s]
        if len(shoulders) == 2:
            person["shoulder_width"] = round(
                ((shoulders[0][0] - shoulders[1][0]) ** 2 + (shoulders[0][1] - shoulders[1][1]) ** 2) ** 0.5,
                1,
            )

        left_hip = kp.get("left_hip")
        right_hip = kp.get("right_hip")
        hips = [h for h in (left_hip, right_hip) if h]
        if shoulders and hips:
            shoulder_y = sum(s[1] for s in shoulders) / len(shoulders)
            hip_y = sum(h[1] for h in hips) / len(hips)
            person["torso_height"] = round(abs(hip_y - shoulder_y), 1)

            legs = [k for k in (left_ankle, right_ankle) if k]
            leg_len = 0.0
            if legs and hips:
                hip_y_avg = sum(h[1] for h in hips) / len(hips)
                leg_len = sum(abs(l[1] - hip_y_avg) for l in legs) / len(legs)

            # A standing person has legs roughly as long as their torso; seated or
            # crouched people have much shorter apparent legs.
            if leg_len > 0 and person["torso_height"] > 0:
                ratio = leg_len / person["torso_height"]
                if ratio >= 1.1:
                    person["posture"] = "standing"
                elif ratio >= 0.7:
                    person["posture"] = "leaning"
                else:
                    person["posture"] = "seated_or_crouched"

        # Phone in hand: a wrist raised to roughly head height (within one head-length).
        head_y = None
        if nose:
            head_y = nose[1]
        elif shoulders:
            head_y = min(s[1] for s in shoulders)
        if head_y is not None:
            head_len = max(1.0, person["torso_height"] * 0.45)
            for wrist_name in ("left_wrist", "right_wrist"):
                wrist = kp.get(wrist_name)
                if not wrist:
                    continue
                if wrist[1] <= head_y + head_len * 0.6:
                    person["phone_in_hand"] = True
                    person["arms_raised"] = True
                    break

        # Carrying a bag: hand below the hip line and offset from the torso centre.
        if hips and shoulders:
            hip_y = max(h[1] for h in hips)
            torso_x = sum(s[0] for s in shoulders) / len(shoulders)
            torso_half_width = max(1.0, person["shoulder_width"] * 0.5)
            for wrist_name in ("left_wrist", "right_wrist"):
                wrist = kp.get(wrist_name)
                if not wrist:
                    continue
                if wrist[1] > hip_y and abs(wrist[0] - torso_x) > torso_half_width * 0.4:
                    person["carrying_bag"] = True
                    break


def match_pose_to_track(pose: Dict[str, Any], bbox: List[float]) -> float:
    """IoU between a pose box and a tracker box, used to pair a body with its track."""
    px1, py1, px2, py2 = pose["bbox"]
    tx1, ty1, tx2, ty2 = bbox
    ix1, iy1 = max(px1, tx1), max(py1, ty1)
    ix2, iy2 = min(px2, tx2), min(py2, ty2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_p = max(0.0, px2 - px1) * max(0.0, py2 - py1)
    area_t = max(0.0, tx2 - tx1) * max(0.0, ty2 - ty1)
    union = area_p + area_t - inter
    return float(inter / union) if union > 0 else 0.0
