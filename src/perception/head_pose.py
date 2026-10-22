import logging
import math
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Generic 3D head geometry (millimetres) in the OpenCV camera convention:
#   +X = image-right (the subject's own left, for a frontal face)
#   +Y = down
#   +Z = into the head (away from the camera)
#
# This handedness matters. If +Z points *out* of the face, the model is mirrored with
# respect to the camera frame and every recovered angle comes out sign-flipped. With
# +Z into the head the model and the camera frame agree exactly, so a frontal face
# solves to R = I.
#
# Scale is irrelevant -- solvePnP only needs the *shape* of the model, not its size.
# The nose tip sits at the origin; the eyes and mouth are set back into the head.
_HEAD_MODEL_3D = {
    "nose": (0.0, 0.0, 0.0),
    "left_eye": (32.0, -25.0, 40.0),
    "right_eye": (-32.0, -25.0, 40.0),
    "left_mouth": (26.0, 60.0, 65.0),
    "right_mouth": (-26.0, 60.0, 65.0),
}

# A head turned further than this is not looking at the camera-facing plane any more.
FACING_YAW_DEG = 25.0
FACING_PITCH_DEG = 20.0


class HeadPoseEstimator:
    """Estimates head yaw/pitch/roll from YuNet's 5 facial landmarks.

    This is the gaze *proxy* the pipeline uses. A full gaze-estimation network needs
    an eye-region model and calibrated cameras to be meaningful; head orientation
    already answers the retail question ("is this person engaged with the display in
    front of them, or looking at their phone / away?") at a fraction of the cost and
    with none of the calibration burden.

    Angle convention (image space, subject facing the camera):
      yaw   > 0 -> subject is turned toward image-right
      pitch > 0 -> subject is looking down
      roll  > 0 -> subject's head is tilted toward image-right
    """

    def __init__(self, focal_scale: float = 1.0):
        # focal_scale lets a caller compensate for a lens narrower/wider than the
        # pinhole default. 1.0 means "focal length equals image width", which is a
        # reasonable average for the wide CCTV lenses this runs on.
        self.focal_scale = focal_scale

    @staticmethod
    def _solve_pose(obj_pts, img_pts, camera_matrix):
        """Runs solvePnP with a solver that accepts a 5-point landmark set.

        YuNet emits five landmarks (two eyes, nose, two mouth corners) and no chin.
        OpenCV's ITERATIVE solver needs six or more points, so it raises on a 5-point
        set -- which is exactly what we have. EPnP works from four points upward and
        is the right choice here; SQPNP and ITERATIVE are kept as fallbacks so a
        future landmark set with more points still works.
        """
        import cv2
        import numpy as np

        last_error = None
        for flag_name in ("SOLVEPNP_EPNP", "SOLVEPNP_SQPNP", "SOLVEPNP_ITERATIVE"):
            flag = getattr(cv2, flag_name, None)
            if flag is None:
                continue
            try:
                success, rvec, tvec = cv2.solvePnP(
                    obj_pts, img_pts, camera_matrix, np.zeros((4, 1)), flags=flag
                )
                if success:
                    return True, rvec, tvec
            except Exception as e:
                last_error = e
        if last_error:
            raise last_error
        return False, None, None

    def estimate(
        self,
        face: Dict[str, Any],
        frame_width: int,
        frame_height: int,
    ) -> Optional[Dict[str, Any]]:
        import cv2
        import numpy as np

        landmarks = face.get("landmarks") or {}
        obj_pts = []
        img_pts = []
        for name, model_pt in _HEAD_MODEL_3D.items():
            lm = landmarks.get(name)
            if not lm:
                continue
            obj_pts.append(model_pt)
            img_pts.append([float(lm[0]), float(lm[1])])

        if len(obj_pts) < 4:
            return None

        focal = max(1.0, frame_width * self.focal_scale)
        camera_matrix = np.array([
            [focal, 0.0, frame_width / 2.0],
            [0.0, focal, frame_height / 2.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)

        try:
            success, rvec, tvec = self._solve_pose(
                np.array(obj_pts, dtype=np.float64),
                np.array(img_pts, dtype=np.float64),
                camera_matrix,
            )
        except Exception as e:
            logger.debug(f"solvePnP failed: {e}")
            return None

        if not success:
            return None

        rotation_matrix, _ = cv2.Rodrigues(rvec)
        R = rotation_matrix
        sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
        if sy > 1e-6:
            # Axis mapping for the model frame above (X right, Y down, Z into head):
            #   rotation about X  -> pitch  (positive = looking down)
            #   rotation about Y  -> yaw    (positive = turned toward image-LEFT)
            #   rotation about Z  -> roll   (positive = head tilted toward image-right)
            pitch = math.atan2(R[2, 1], R[2, 2])
            yaw_std = math.atan2(-R[2, 0], sy)
            roll = math.atan2(R[1, 0], R[0, 0])
        else:
            pitch = math.atan2(-R[1, 2], R[1, 1])
            yaw_std = 0.0
            roll = math.atan2(-R[2, 0], sy)

        # The published convention is yaw > 0 = turned toward image-RIGHT, which is the
        # negation of the raw Y-axis rotation.
        yaw_deg = round(math.degrees(-yaw_std), 1)
        pitch_deg = round(math.degrees(pitch), 1)
        roll_deg = round(math.degrees(roll), 1)

        facing = abs(yaw_deg) <= FACING_YAW_DEG and abs(pitch_deg) <= FACING_PITCH_DEG

        return {
            "yaw": yaw_deg,
            "pitch": pitch_deg,
            "roll": roll_deg,
            "facing_camera": facing,
            "attention_score": round(_attention_score(yaw_deg, pitch_deg, roll_deg), 3),
        }


def _attention_score(yaw: float, pitch: float, roll: float) -> float:
    """0..1 engagement proxy: how squarely the subject faces the camera plane.

    A squared cosine falloff keeps the curve smooth so a person slowly turning their
    head does not flip between "engaged" and "not" on a single frame.
    """
    yaw_term = math.cos(math.radians(min(90.0, abs(yaw))))
    pitch_term = math.cos(math.radians(min(90.0, abs(pitch))))
    roll_term = math.cos(math.radians(min(45.0, abs(roll))))
    score = (yaw_term ** 2) * 0.6 + (pitch_term ** 2) * 0.25 + (roll_term ** 2) * 0.15
    return max(0.0, min(1.0, score))
