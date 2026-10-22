"""Soft person ReID (OSNet) — privacy-gated, default-off.

Body-crop embeddings for *future* intra-cam repair and adjacent-cam handoff.
Does **not** implement face ReID, multi-day galleries, or CRM identity.

Loading prefers an optional ``torchreid`` FeatureExtractor when installed.
Weights live under ``models/pack/03-reid/`` (segregated; not production-wired
until ``models.reid.enabled: true``).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Prefer smaller edge-viable weight first; x0.5 is stronger when present.
DEFAULT_WEIGHT_CANDIDATES = (
    "models/pack/03-reid/osnet-x0_25/osnet_x0_25_msmt17.pt",
    "models/pack/03-reid/osnet-x0_5/osnet_x0_5_msmt17.pth",
)


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


class SoftReIdExtractor:
    """Optional OSNet body-embedding extractor.

    Status contract (honest):
    - ``weights_present`` — pack file on disk
    - ``loaded`` — torchreid FeatureExtractor warmed
    - ``enabled`` — config flag (must be True *and* loaded to extract)
    """

    def __init__(
        self,
        weights: Optional[str] = None,
        device: str = "cpu",
        enabled: bool = False,
        base_dir: Optional[str] = None,
    ):
        self.enabled = bool(enabled)
        self.device = device or "cpu"
        self.base_dir = base_dir or os.getcwd()
        self.weights_path = self._resolve_weights(weights)
        self.weights_present = bool(self.weights_path and os.path.isfile(self.weights_path))
        self.loaded = False
        self.load_error: Optional[str] = None
        self._extractor = None
        self.model_name = self._infer_model_name(self.weights_path)
        self.last_extract_ms: float = 0.0

        if self.enabled and self.weights_present:
            self._try_load()
        elif self.enabled and not self.weights_present:
            self.load_error = "ReID weights missing — run python scripts/download_pack_models.py"
            logger.warning(self.load_error)
        elif not self.enabled:
            logger.info(
                "Soft ReID default-off (DPDP). Pack weight %s; set models.reid.enabled: true to load.",
                "present" if self.weights_present else "absent",
            )

    def _resolve_weights(self, weights: Optional[str]) -> Optional[str]:
        candidates: List[str] = []
        if weights:
            candidates.append(weights)
        candidates.extend(DEFAULT_WEIGHT_CANDIDATES)
        for rel in candidates:
            path = rel if os.path.isabs(rel) else os.path.join(self.base_dir, rel)
            if os.path.isfile(path) and os.path.getsize(path) > 1_000_000:
                return path
        return weights if weights and os.path.isabs(weights) else (
            os.path.join(self.base_dir, weights) if weights else None
        )

    @staticmethod
    def _infer_model_name(path: Optional[str]) -> str:
        if not path:
            return "osnet_x0_25"
        name = os.path.basename(path).lower()
        if "x0_5" in name or "x0.5" in name:
            return "osnet_x0_5"
        if "x0_75" in name:
            return "osnet_x0_75"
        if "x1_0" in name or "x1.0" in name:
            return "osnet_x1_0"
        return "osnet_x0_25"

    def _try_load(self) -> None:
        try:
            from torchreid.utils import FeatureExtractor  # type: ignore
        except Exception as e:
            self.load_error = (
                f"torchreid not installed ({e}). Weights at {self.weights_path} — "
                "pip install torchreid (or leave reid disabled)."
            )
            logger.warning(self.load_error)
            return
        try:
            self._extractor = FeatureExtractor(
                model_name=self.model_name,
                model_path=self.weights_path,
                device=self.device,
            )
            self.loaded = True
            self.load_error = None
            logger.info("Soft ReID loaded (%s) from %s", self.model_name, self.weights_path)
        except Exception as e:
            self.load_error = str(e)
            self.loaded = False
            logger.error("Soft ReID failed to load: %s", e)

    @property
    def active(self) -> bool:
        return self.enabled and self.loaded and self._extractor is not None

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "weights_present": self.weights_present,
            "weights_path": self.weights_path,
            "model_name": self.model_name,
            "loaded": self.loaded,
            "active": self.active,
            "device": self.device,
            "load_error": self.load_error,
            "last_extract_ms": self.last_extract_ms,
            "cross_cam_fusion": False,  # honest: fusion module not shipped
            "note": (
                "Body soft-ReID only; no face ID; no multi-day gallery; "
                "cross-cam global_person_id requires NTP + overlap + fusion (Future)."
            ),
        }

    def extract_crops(self, crops_bgr: List[Any]) -> Optional[Any]:
        """Return (N, D) embeddings or None if inactive / empty."""
        if not self.active or not crops_bgr:
            return None
        t0 = time.perf_counter()
        try:
            # torchreid FeatureExtractor accepts a list of ndarray / paths
            feats = self._extractor(crops_bgr)
            self.last_extract_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            return feats
        except Exception as e:
            logger.debug("ReID extract failed: %s", e)
            return None
