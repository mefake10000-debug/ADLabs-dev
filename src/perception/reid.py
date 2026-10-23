"""Soft person ReID (OSNet / YouTu) — privacy-gated, session-scoped.

Body-crop embeddings for intra-cam repair and *future* adjacent-cam handoff.
Does **not** implement face ReID, multi-day galleries, or CRM identity.

Backends (first that loads wins):
1. ``torchreid`` FeatureExtractor when installed + ``.pth`` weights
2. OSNet ONNX (``osnet_x0_25_msmt17.onnx``) via onnxruntime
3. OpenCV Zoo YouTu ONNX (``person_reid_youtu_2021nov.onnx``)

Weights live under ``models/pack/03-reid/``. Enable with ``models.reid.enabled: true``
(default on this branch when pack weights are present — still session-scoped only).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Prefer verified kaiyangzhou OSNet pack (download_pack_models.py), then ONNX, then legacy.
DEFAULT_PTH_CANDIDATES = (
    "models/pack/03-reid/osnet_x0_25_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth",
    "models/pack/03-reid/osnet_x1_0_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth",
    "models/pack/03-reid/osnet-x0_25/osnet_x0_25_msmt17.pt",
    "models/pack/03-reid/osnet-x0_5/osnet_x0_5_msmt17.pth",
)
DEFAULT_ONNX_CANDIDATES = (
    "models/pack/03-reid/osnet_x0_25_msmt17.onnx",
    "models/pack/03-reid/person_reid_youtu_2021nov.onnx",
)

# ImageNet-ish normalization used by torchreid / common OSNet ONNX exports.
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)


@dataclass
class ReIdEmbedding:
    camera_id: str
    track_id: int
    embedding: Any  # numpy vector when available
    capture_ts_utc: float
    foot_xy: Optional[Tuple[float, float]] = None


@dataclass
class SoftReIdGallery:
    """Day-local in-process gallery. Wipe at close; never cloud-sync vectors."""

    max_age_seconds: float = 3600.0
    max_entries: int = 256
    _items: List[ReIdEmbedding] = field(default_factory=list)

    def add(self, item: ReIdEmbedding) -> None:
        self._items.append(item)
        self.prune(item.capture_ts_utc)

    def prune(self, now: float) -> None:
        cutoff = now - self.max_age_seconds
        self._items = [x for x in self._items if x.capture_ts_utc >= cutoff]
        if len(self._items) > self.max_entries:
            self._items = self._items[-self.max_entries :]

    def clear(self) -> None:
        self._items.clear()

    def size(self) -> int:
        return len(self._items)

    def same_camera_count(self, camera_id: str) -> int:
        return sum(1 for x in self._items if x.camera_id == camera_id)


class SoftReIdExtractor:
    """Optional body-embedding extractor (torchreid .pth or ONNX).

    Status contract (honest):
    - ``weights_present`` — pack file on disk
    - ``loaded`` — backend warmed
    - ``enabled`` — config flag (must be True *and* loaded to extract)
    - ``backend`` — ``torchreid`` | ``onnx_osnet`` | ``onnx_youtu`` | None
    """

    def __init__(
        self,
        weights: Optional[str] = None,
        device: str = "cpu",
        enabled: bool = False,
        base_dir: Optional[str] = None,
        onnx_weights: Optional[str] = None,
    ):
        self.enabled = bool(enabled)
        self.device = device or "cpu"
        self.base_dir = base_dir or os.getcwd()
        self.weights_path = self._resolve_weights(weights, DEFAULT_PTH_CANDIDATES)
        self.onnx_path = self._resolve_weights(onnx_weights, DEFAULT_ONNX_CANDIDATES)
        self.weights_present = bool(
            (self.weights_path and os.path.isfile(self.weights_path))
            or (self.onnx_path and os.path.isfile(self.onnx_path))
        )
        self.loaded = False
        self.load_error: Optional[str] = None
        self.backend: Optional[str] = None
        self._extractor = None
        self._session = None
        self._input_name: Optional[str] = None
        self._fixed_batch: Optional[int] = None
        self.model_name = self._infer_model_name(self.weights_path or self.onnx_path)
        self.last_extract_ms: float = 0.0
        self.embedding_dim: Optional[int] = None

        if self.enabled and self.weights_present:
            self._try_load()
        elif self.enabled and not self.weights_present:
            self.load_error = "ReID weights missing — run python scripts/download_pack_models.py"
            logger.warning(self.load_error)
        elif not self.enabled:
            logger.info(
                "Soft ReID off (DPDP). Pack weight %s; set models.reid.enabled: true to load.",
                "present" if self.weights_present else "absent",
            )

    def _resolve_weights(
        self, weights: Optional[str], candidates: Tuple[str, ...]
    ) -> Optional[str]:
        ordered: List[str] = []
        if weights:
            ordered.append(weights)
        ordered.extend(candidates)
        for rel in ordered:
            path = rel if os.path.isabs(rel) else os.path.join(self.base_dir, rel)
            if os.path.isfile(path) and os.path.getsize(path) > 100_000:
                return path
        if weights:
            return weights if os.path.isabs(weights) else os.path.join(self.base_dir, weights)
        return None

    @staticmethod
    def _infer_model_name(path: Optional[str]) -> str:
        if not path:
            return "osnet_x0_25"
        name = os.path.basename(path).lower()
        if "youtu" in name:
            return "youtu_reid"
        if "x0_5" in name or "x0.5" in name:
            return "osnet_x0_5"
        if "x0_75" in name:
            return "osnet_x0_75"
        if "x1_0" in name or "x1.0" in name:
            return "osnet_x1_0"
        return "osnet_x0_25"

    def _try_load(self) -> None:
        # Prefer torchreid when .pth exists and package is installed.
        if self.weights_path and self.weights_path.lower().endswith((".pth", ".pt")):
            if self._try_load_torchreid():
                return
        # ONNX path (osnet then youtu via resolve order)
        if self.onnx_path and self._try_load_onnx(self.onnx_path):
            return
        # Last resort: try any remaining ONNX candidates not already tried
        for rel in DEFAULT_ONNX_CANDIDATES:
            path = rel if os.path.isabs(rel) else os.path.join(self.base_dir, rel)
            if self.onnx_path and os.path.abspath(path) == os.path.abspath(self.onnx_path):
                continue
            if os.path.isfile(path) and self._try_load_onnx(path):
                self.onnx_path = path
                return
        if not self.load_error:
            self.load_error = (
                "No ReID backend available (torchreid missing and ONNX load failed). "
                f"pth={self.weights_path} onnx={self.onnx_path}"
            )
        logger.warning(self.load_error)

    def _try_load_torchreid(self) -> bool:
        try:
            from torchreid.utils import FeatureExtractor  # type: ignore
        except Exception as e:
            self.load_error = (
                f"torchreid not installed ({e}); will try ONNX fallback."
            )
            logger.info(self.load_error)
            return False
        try:
            self._extractor = FeatureExtractor(
                model_name=self.model_name if self.model_name.startswith("osnet") else "osnet_x0_25",
                model_path=self.weights_path,
                device=self.device,
            )
            self.loaded = True
            self.backend = "torchreid"
            self.load_error = None
            self.model_name = self._infer_model_name(self.weights_path)
            logger.info("Soft ReID loaded (torchreid %s) from %s", self.model_name, self.weights_path)
            return True
        except Exception as e:
            self.load_error = f"torchreid load failed: {e}"
            logger.warning(self.load_error)
            return False

    def _try_load_onnx(self, path: str) -> bool:
        try:
            import onnxruntime as ort
        except Exception as e:
            self.load_error = f"onnxruntime missing ({e})"
            return False
        try:
            sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
            inp = sess.get_inputs()[0]
            self._session = sess
            self._input_name = inp.name
            shape = list(inp.shape)
            # Fixed batch (osnet export uses 16) vs dynamic (youtu uses 'batch_size')
            if len(shape) >= 1 and isinstance(shape[0], int) and shape[0] > 0:
                self._fixed_batch = int(shape[0])
            else:
                self._fixed_batch = None
            name = os.path.basename(path).lower()
            self.backend = "onnx_youtu" if "youtu" in name else "onnx_osnet"
            self.model_name = self._infer_model_name(path)
            self.loaded = True
            self.load_error = None
            logger.info("Soft ReID loaded (%s) from %s", self.backend, path)
            return True
        except Exception as e:
            self.load_error = f"ONNX ReID load failed ({path}): {e}"
            logger.warning(self.load_error)
            self._session = None
            return False

    @property
    def active(self) -> bool:
        return self.enabled and self.loaded and (
            self._extractor is not None or self._session is not None
        )

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "weights_present": self.weights_present,
            "weights_path": self.weights_path,
            "onnx_path": self.onnx_path,
            "model_name": self.model_name,
            "backend": self.backend,
            "loaded": self.loaded,
            "active": self.active,
            "device": self.device,
            "load_error": self.load_error,
            "last_extract_ms": self.last_extract_ms,
            "embedding_dim": self.embedding_dim,
            "session_scoped": True,
            "cross_cam_fusion": False,  # honest: fusion module not shipped
            "note": (
                "Body soft-ReID only; session-scoped gallery; no face ID; "
                "no multi-day gallery; cross-cam global_person_id requires "
                "NTP + overlap + fusion (Future)."
            ),
        }

    @staticmethod
    def _preprocess_crops(crops_bgr: List[Any]) -> np.ndarray:
        """BGR crops → NCHW float32 ImageNet-normalized, H=256 W=128."""
        batch = []
        for crop in crops_bgr:
            if crop is None or getattr(crop, "size", 0) == 0:
                batch.append(np.zeros((3, 256, 128), dtype=np.float32))
                continue
            import cv2

            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb, (128, 256), interpolation=cv2.INTER_LINEAR)
            chw = resized.astype(np.float32).transpose(2, 0, 1) / 255.0
            batch.append(chw)
        arr = np.stack(batch, axis=0)
        arr = (arr - _IMAGENET_MEAN) / _IMAGENET_STD
        return arr.astype(np.float32)

    def extract_crops(self, crops_bgr: List[Any]) -> Optional[Any]:
        """Return (N, D) float embeddings or None if inactive / empty."""
        if not self.active or not crops_bgr:
            return None
        t0 = time.perf_counter()
        try:
            if self._extractor is not None:
                feats = self._extractor(crops_bgr)
                if hasattr(feats, "detach"):
                    feats = feats.detach().cpu().numpy()
                feats = np.asarray(feats, dtype=np.float32)
            else:
                feats = self._extract_onnx(crops_bgr)
            if feats is None:
                return None
            # L2-normalize for cosine compare later
            norms = np.linalg.norm(feats, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-8)
            feats = feats / norms
            self.embedding_dim = int(feats.shape[1]) if feats.ndim == 2 else None
            self.last_extract_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            return feats
        except Exception as e:
            logger.debug("ReID extract failed: %s", e)
            return None

    def _extract_onnx(self, crops_bgr: List[Any]) -> Optional[np.ndarray]:
        assert self._session is not None and self._input_name
        n = len(crops_bgr)
        tensor = self._preprocess_crops(crops_bgr)
        if self._fixed_batch:
            # Pad/truncate to fixed batch (osnet export = 16)
            b = self._fixed_batch
            if n > b:
                tensor = tensor[:b]
                n = b
            elif n < b:
                pad = np.zeros((b - n, 3, 256, 128), dtype=np.float32)
                tensor = np.concatenate([tensor, pad], axis=0)
        outs = self._session.run(None, {self._input_name: tensor})
        feats = np.asarray(outs[0], dtype=np.float32)
        # YouTu: [N, 768, 1, 1] → [N, 768]
        if feats.ndim == 4:
            feats = feats.reshape(feats.shape[0], -1)
        return feats[:n]
