"""RTMPose top-down ankle / foot estimator (Apache-2.0 ONNX via rtmlib).

Prefers ``rtmlib.RTMPose`` when importable; falls back to a minimal ONNX Runtime
SimCC decode so foot points still work if rtmlib is offline. Person boxes come
from Ultralytics YOLO (or RF-DETR) — this module does not re-detect people.

Fallback when pose weights are missing: callers use bbox bottom-center.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# COCO-17 indices (body7 RTMPose export).
_LEFT_ANKLE = 15
_RIGHT_ANKLE = 16

# Thin skeleton edges for overlay (COCO-17 pairs).
COCO17_SKELETON: Tuple[Tuple[int, int], ...] = (
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (0, 5), (0, 6),
)

KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


def resolve_rtmpose_onnx(pack_root: Optional[str] = None, prefer: str = "t") -> Optional[Path]:
    """Return path to rtmpose-t.onnx or rtmpose-s.onnx under models/pack/07-pose."""
    root = Path(pack_root or os.path.join(os.getcwd(), "models", "pack", "07-pose"))
    if not root.is_dir():
        return None
    order = ("rtmpose-t.onnx", "rtmpose-s.onnx") if prefer in ("t", "tiny") else (
        "rtmpose-s.onnx", "rtmpose-t.onnx",
    )
    for name in order:
        p = root / name
        if p.is_file() and p.stat().st_size > 1000:
            return p
    # Any leftover end2end / hashed onnx
    for p in sorted(root.glob("*.onnx")):
        if p.stat().st_size > 1000:
            return p
    return None


def foot_from_ankles(
    keypoints: Sequence[Sequence[float]],
    scores: Optional[Sequence[float]] = None,
    min_score: float = 0.25,
) -> Optional[Tuple[float, float]]:
    """Ground contact ≈ ankle midpoint (x) + lower ankle (y)."""
    if keypoints is None or len(keypoints) <= _RIGHT_ANKLE:
        return None
    pts = []
    for idx in (_LEFT_ANKLE, _RIGHT_ANKLE):
        if scores is not None and idx < len(scores) and float(scores[idx]) < min_score:
            continue
        x, y = float(keypoints[idx][0]), float(keypoints[idx][1])
        if x <= 1.0 and y <= 1.0:
            continue
        pts.append((x, y))
    if not pts:
        return None
    return (
        sum(p[0] for p in pts) / len(pts),
        max(p[1] for p in pts),
    )


def bbox_foot(bbox: Sequence[float]) -> Tuple[float, float]:
    """AABB bottom-center — fallback when pose is offline."""
    x1, y1, x2, y2 = [float(v) for v in bbox]
    return ((x1 + x2) * 0.5, y2)


class RTMPoseFootEstimator:
    """Top-down RTMPose on person crops → keypoints + foot point per bbox."""

    def __init__(
        self,
        onnx_path: Optional[str] = None,
        device: str = "cpu",
        prefer: str = "t",
        input_size: Tuple[int, int] = (192, 256),  # (w, h) — rtmlib convention
    ):
        self.device = device
        self.input_size = input_size
        self._backend = "none"
        self._pose = None
        self._session = None
        self.calls = 0
        self.onnx_path: Optional[Path] = None
        path = Path(onnx_path) if onnx_path else resolve_rtmpose_onnx(prefer=prefer)
        if path is None:
            logger.info("RTMPose ONNX not on disk — foot falls back to bbox bottom-center.")
            return
        self.onnx_path = path
        self._try_rtmlib(path, device)
        if self._pose is None:
            self._try_ort(path)

    @property
    def active(self) -> bool:
        return self._pose is not None or self._session is not None

    @property
    def backend(self) -> str:
        return self._backend

    def _try_rtmlib(self, path: Path, device: str) -> None:
        try:
            from rtmlib import RTMPose  # type: ignore
        except Exception as e:  # noqa: BLE001
            logger.info("rtmlib unavailable (%s); using ONNX Runtime SimCC fallback.", e)
            return
        try:
            self._pose = RTMPose(
                onnx_model=str(path),
                model_input_size=self.input_size,
                backend="onnxruntime",
                device=device if device in ("cpu", "cuda", "mps") else "cpu",
            )
            # rtmlib otherwise gives every session an unrestricted CPU pool.
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            self._pose.session = ort.InferenceSession(
                str(path), sess_options=options, providers=self._pose.session.get_providers()
            )
            self._backend = "rtmlib"
            logger.info("RTMPose ready via rtmlib: %s", path.name)
        except Exception as e:  # noqa: BLE001
            logger.warning("rtmlib.RTMPose failed (%s); trying ORT fallback.", e)
            self._pose = None

    def _try_ort(self, path: Path) -> None:
        try:
            import onnxruntime as ort
        except Exception as e:  # noqa: BLE001
            logger.warning("onnxruntime missing for RTMPose fallback: %s", e)
            return
        try:
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            self._session = ort.InferenceSession(
                str(path), sess_options=options, providers=["CPUExecutionProvider"]
            )
            self._backend = "ort-simcc"
            logger.info("RTMPose ready via ORT SimCC: %s", path.name)
        except Exception as e:  # noqa: BLE001
            logger.error("RTMPose ORT load failed: %s", e)
            self._session = None

    def estimate_on_bboxes(
        self,
        frame: Any,
        bboxes: Sequence[Sequence[float]],
    ) -> List[Dict[str, Any]]:
        """Return one pose dict per bbox (keypoints, foot_point, scores)."""
        if frame is None or not bboxes:
            return []
        if self.active:
            self.calls += 1
        if self._pose is not None:
            return self._estimate_rtmlib(frame, bboxes)
        if self._session is not None:
            return self._estimate_ort(frame, bboxes)
        return []

    def _estimate_rtmlib(
        self, frame: Any, bboxes: Sequence[Sequence[float]]
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        arr = np.asarray(bboxes, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[1] < 4:
            return out
        try:
            keypoints, scores = self._pose(frame, arr[:, :4])
        except Exception as e:  # noqa: BLE001
            logger.debug("rtmlib pose failed: %s", e)
            return out
        keypoints = np.asarray(keypoints)
        scores = np.asarray(scores) if scores is not None else None
        for i in range(len(bboxes)):
            kps = keypoints[i] if i < len(keypoints) else None
            sc = scores[i] if scores is not None and i < len(scores) else None
            out.append(self._pack(bboxes[i], kps, sc))
        return out

    def _estimate_ort(
        self, frame: Any, bboxes: Sequence[Sequence[float]]
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        h, w = frame.shape[:2]
        inp_w, inp_h = self.input_size
        for bbox in bboxes:
            x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
            x1i, y1i = max(0, int(x1)), max(0, int(y1))
            x2i, y2i = min(w, int(x2)), min(h, int(y2))
            if x2i - x1i < 8 or y2i - y1i < 16:
                out.append(self._pack(bbox, None, None))
                continue
            crop = frame[y1i:y2i, x1i:x2i]
            blob = self._preprocess(crop, inp_w, inp_h)
            try:
                simcc_x, simcc_y = self._session.run(None, {"input": blob})
            except Exception as e:  # noqa: BLE001
                logger.debug("ORT pose fail: %s", e)
                out.append(self._pack(bbox, None, None))
                continue
            kps, sc = self._decode_simcc(simcc_x[0], simcc_y[0], inp_w, inp_h)
            # Map crop → frame
            sx = (x2i - x1i) / float(inp_w)
            sy = (y2i - y1i) / float(inp_h)
            mapped = [[x1i + p[0] * sx, y1i + p[1] * sy] for p in kps]
            out.append(self._pack(bbox, mapped, sc))
        return out

    @staticmethod
    def _preprocess(crop: Any, inp_w: int, inp_h: int) -> np.ndarray:
        import cv2

        resized = cv2.resize(crop, (inp_w, inp_h), interpolation=cv2.INTER_LINEAR)
        # ImageNet mean/std, BGR→RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32)
        mean = np.array([123.675, 116.28, 103.53], dtype=np.float32)
        std = np.array([58.395, 57.12, 57.375], dtype=np.float32)
        rgb = (rgb - mean) / std
        return rgb.transpose(2, 0, 1)[None, ...]

    @staticmethod
    def _decode_simcc(
        simcc_x: np.ndarray, simcc_y: np.ndarray, inp_w: int, inp_h: int, split: float = 2.0
    ) -> Tuple[List[List[float]], List[float]]:
        # simcc_x: [K, W*split], simcc_y: [K, H*split]
        x_idx = np.argmax(simcc_x, axis=-1).astype(np.float32)
        y_idx = np.argmax(simcc_y, axis=-1).astype(np.float32)
        # Softmax-ish confidence proxy from peak vs mean
        x_peak = np.max(simcc_x, axis=-1)
        y_peak = np.max(simcc_y, axis=-1)
        scores = (1.0 / (1.0 + np.exp(-0.5 * (x_peak + y_peak)))).tolist()
        xs = (x_idx / split).tolist()
        ys = (y_idx / split).tolist()
        kps = [[float(xs[i]), float(ys[i])] for i in range(len(xs))]
        return kps, [float(s) for s in scores]

    @staticmethod
    def _pack(
        bbox: Sequence[float],
        keypoints: Any,
        scores: Any,
    ) -> Dict[str, Any]:
        foot = None
        named: Dict[str, List[float]] = {}
        if keypoints is not None:
            kps = np.asarray(keypoints, dtype=np.float32)
            sc = np.asarray(scores, dtype=np.float32) if scores is not None else None
            foot_t = foot_from_ankles(kps, sc)
            if foot_t is not None:
                foot = [round(foot_t[0], 1), round(foot_t[1], 1)]
            for i, name in enumerate(KEYPOINT_NAMES):
                if i >= len(kps):
                    break
                if sc is not None and i < len(sc) and float(sc[i]) < 0.2:
                    continue
                named[name] = [round(float(kps[i][0]), 1), round(float(kps[i][1]), 1)]
        return {
            "bbox": [round(float(v), 1) for v in bbox[:4]],
            "keypoints": named,
            "keypoints_xy": (
                [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in keypoints]
                if keypoints is not None
                else []
            ),
            "keypoint_scores": (
                [round(float(s), 3) for s in scores] if scores is not None else []
            ),
            "foot_point": foot,
            "backend": "rtmpose",
        }
