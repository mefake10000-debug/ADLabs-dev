import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Perceptual models run at different cadences. The person detector is the only one that
# needs every frame; everything else is an enrichment that can run on a slower tier
# without degrading the core footfall/dwell/queue numbers.
TIER_FAST = "fast"
TIER_SLOW = "slow"


@dataclass
class ModelSpec:
    """Declarative description of one perceptual model.

    Weights are resolved lazily: a machine that has no `models/` directory (a fresh clone,
    or a CI box) still starts the pipeline and simply reports the models as unavailable,
    instead of dying at import time. `required` models (the person detector) raise, because
    a pipeline without them would report plausible-looking zeros.
    """

    key: str
    kind: str                    # "ultralytics" | "onnx" | "clip"
    path: str
    capability: str              # "person" | "pose" | "face" | "demographics" | "product" | "shelf_zero_shot"
    tier: str = TIER_SLOW
    task: str = "detect"         # ultralytics task: detect | pose | segment
    enabled: bool = True
    required: bool = False
    aliases: List[str] = field(default_factory=list)   # fallback checkpoints, first existing wins
    params: Dict[str, Any] = field(default_factory=dict)

    def candidates(self) -> List[str]:
        return [self.path, *self.aliases]

    def resolved_path(self, base_dir: str) -> str:
        """Absolute path to the primary weights, resolved against the project root.

        `models/` is bind-mounted in Docker and git-ignored for the large checkpoints,
        so every spec stores a project-relative path.
        """
        if os.path.isabs(self.path):
            return self.path
        return os.path.join(base_dir, self.path)

    def first_existing_path(self, base_dir: str) -> str:
        """First candidate that actually exists on disk (primary, then aliases).

        New open weights land in `models/pack/…` (download_pack_models.py) and
        `weights/`; the same YAML works on any clone because the list is resolved
        per machine instead of being hardcoded to one environment.
        """
        for candidate in self.candidates():
            path = candidate if os.path.isabs(candidate) else os.path.join(base_dir, candidate)
            if os.path.exists(path):
                return path
        return self.resolved_path(base_dir)

    def matched_candidate(self, base_dir: str) -> Optional[str]:
        """The candidate string that `first_existing_path` picked, None for the primary."""
        resolved = self.first_existing_path(base_dir)
        for candidate in self.candidates()[1:]:
            path = candidate if os.path.isabs(candidate) else os.path.join(base_dir, candidate)
            try:
                if os.path.samefile(path, resolved):
                    return candidate
            except OSError:
                continue  # candidate missing from this environment; keep walking
        return None


class ModelRegistry:
    """Holds the model specs for one camera pipeline and loads them on demand.

    Loading is deliberately lazy and per-key: enabling the face/demographics enrichment
    must not cost anything on a machine that never asked for it, and a single failed
    model must not take down the whole pipeline (it degrades to "that enrichment is
    unavailable", which the health endpoint reports).
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self._specs: Dict[str, ModelSpec] = {}
        self._loaded: Dict[str, Any] = {}
        # Capabilities instantiated outside the registry's own loaders (e.g. the
        # YuNet FaceDetector) still have to show as loaded in status().
        self._loaded_externally: set = set()
        self._errors: Dict[str, str] = {}
        self._load_times: Dict[str, float] = {}

    def register(self, spec: ModelSpec):
        self._specs[spec.key] = spec
        return spec

    def register_all(self, specs: List[ModelSpec]):
        for spec in specs:
            self.register(spec)
        return self

    def spec(self, key: str) -> Optional[ModelSpec]:
        return self._specs.get(key)

    def is_loaded(self, key: str) -> bool:
        return key in self._loaded

    def error(self, key: str) -> Optional[str]:
        return self._errors.get(key)

    def load_time_ms(self, key: str) -> float:
        return round(self._load_times.get(key, 0.0) * 1000.0, 1)

    def available(self, key: str) -> bool:
        return key in self._loaded

    def mark_loaded(self, key: str):
        """Records a capability that was instantiated elsewhere as loaded (status only)."""
        self._loaded_externally.add(key)
        self._errors.pop(key, None)

    def get(self, key: str) -> Optional[Any]:
        """Returns the loaded model instance, or None if it failed to load.

        Failed loads are cached as errors so a broken checkpoint does not cause a
        repeated multi-second load attempt on every frame.
        """
        if key in self._loaded:
            return self._loaded[key]
        if key in self._errors:
            return None
        spec = self._specs.get(key)
        if spec is None:
            self._errors[key] = "not registered"
            return None

        path = spec.first_existing_path(self.base_dir)
        started = time.time()
        try:
            if spec.kind == "ultralytics":
                model = self._load_ultralytics(spec, path)
            elif spec.kind == "onnx":
                model = self._load_onnx(spec, path)
            elif spec.kind == "reid":
                model = self._load_reid(spec, path)
            elif spec.kind == "clip":
                model = self._load_clip(spec, path)
            else:
                raise ValueError(f"unknown model kind '{spec.kind}'")
        except Exception as e:
            self._errors[key] = str(e)
            if spec.required:
                raise RuntimeError(
                    f"Required model '{spec.key}' ({spec.path}) failed to load: {e}"
                ) from e
            logger.error(f"Model '{spec.key}' unavailable ({spec.path}): {e}")
            return None

        self._loaded[key] = model
        self._load_times[key] = time.time() - started
        logger.info(
            f"Model '{spec.key}' loaded from {spec.path} in {self.load_time_ms(key)}ms"
        )
        return model

    @staticmethod
    def _load_ultralytics(spec: ModelSpec, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"weights not found at {path} (run scripts/download/download_models.py)"
            )
        from ultralytics import YOLO
        model = YOLO(path)
        model.to(spec.params.get("device", "auto"))
        return model

    @staticmethod
    def _load_onnx(spec: ModelSpec, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"weights not found at {path} (run scripts/download/download_models.py)"
            )
        import onnxruntime as ort
        providers = spec.params.get("providers")
        if not providers:
            providers = (
                ["CoreMLExecutionProvider", "CPUExecutionProvider"]
                if _coreml_available()
                else ["CPUExecutionProvider"]
            )
        session_options = None
        threads = spec.params.get("intra_op_num_threads")
        if threads:
            # The enrichment tier shares the machine with the fast tier. Letting
            # onnxruntime spin up one worker per core for a 224x224 inference
            # oversubscribes the CPU and measurably slows the detector down.
            session_options = ort.SessionOptions()
            session_options.intra_op_num_threads = int(threads)
            session_options.inter_op_num_threads = 1
        if session_options is not None:
            session = ort.InferenceSession(path, sess_options=session_options, providers=providers)
        else:
            session = ort.InferenceSession(path, providers=providers)
        return session

    @staticmethod
    def _load_reid(spec: ModelSpec, path: str):
        """OSNet person-ReID checkpoints from models/pack/03-reid.

        Two formats, chosen by extension:
          .onnx -> onnxruntime (CPU-pinned; verified contract: input [16,3,256,128],
                   output [16,512]. The export has a FIXED batch of 16 -- consumers
                   must pad/truncate to 16 crops per call).
          .pth  -> torchreid checkpoint (deep-person-reid package required, not in
                   requirements-edge; the import error is what you see in status).
        """
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"weights not found at {path} (run scripts/download/download_pack_models.py)"
            )
        if path.endswith(".onnx"):
            import onnxruntime as ort
            providers = spec.params.get("providers") or ["CPUExecutionProvider"]
            session_options = ort.SessionOptions()
            threads = spec.params.get("intra_op_num_threads")
            if threads:
                session_options.intra_op_num_threads = int(threads)
                session_options.inter_op_num_threads = 1
            session = ort.InferenceSession(path, sess_options=session_options, providers=providers)
            ins, out = session.get_inputs()[0], session.get_outputs()[0]
            if out.shape[-1] != 512:
                raise ValueError(f"unexpected ReID output dim {out.shape} (expected *x512)")
            if ins.shape[0] != 16:
                raise ValueError(
                    f"unexpected ReID batch dim {ins.shape} (export verified as [16,3,256,128]; "
                    "consumers must pad to 16 crops"
                )
            return session
        import torchreid  # noqa: F401  (raises with a clear message if absent)
        import torch
        model = torchreid.models.build_model(
            name="osnet_x0_25", num_classes=17, pretrained=False, use_gpu=False
        )
        torchreid.utils.load_pretrained_weights(model, path)
        return model.eval()

    @staticmethod
    def _load_clip(spec: ModelSpec, path: str):
        """OpenAI CLIP checkpoint (weights/clip/ViT-B-32.pt or the HF-resident copy).

        Both loaders are import-guarded: the 05-open-vocab pack plus a declared
        consumer later only needs the checkpoint, never a hard pip dependency.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"weights not found at {path} (run scripts/download/download_pack_models.py)"
            )
        device = spec.params.get("device", "cpu")
        try:
            import torch
            import clip as openai_clip  # pip: git+https://github.com/openai/CLIP
            model, _ = openai_clip.load(path, device=device)
            return model.to(device).eval()
        except ImportError:
            pass
        import open_clip  # pip: open_clip_torch
        model, _, _ = open_clip.create_model_and_transforms("ViT-B-32", pretrained=path)
        return model.to(device).eval()

    def status(self) -> List[Dict[str, Any]]:
        """Machine-readable status for every registered model (health endpoint / dashboard)."""
        out = []
        for key, spec in self._specs.items():
            resolved = spec.first_existing_path(self.base_dir)
            out.append({
                "key": key,
                "capability": spec.capability,
                "tier": spec.tier,
                "task": spec.task,
                "path": spec.path,
                "aliases": spec.aliases,
                "resolved": resolved,
                "weight_source": spec.matched_candidate(self.base_dir) or spec.path,
                "enabled": spec.enabled,
                "loaded": key in self._loaded or key in self._loaded_externally,
                "load_time_ms": self.load_time_ms(key),
                "error": self._errors.get(key),
            })
        return out


def resolve_weights_path(candidates: List[str], base_dir: str) -> str:
    """First existing checkpoint among `candidates`, else the first candidate as given.

    Used for config entries expressed as a list (perception.model_name) so a clean
    clone with only models/pack weights and a checkout with legacy paths both boot.
    """
    first = None
    for candidate in candidates:
        path = candidate if os.path.isabs(candidate) else os.path.join(base_dir, candidate)
        if first is None:
            first = path
        if os.path.exists(path):
            return path
    return first if first is not None else (candidates[0] if candidates else "")


def _coreml_available() -> bool:
    try:
        import onnxruntime as ort
        return "CoreMLExecutionProvider" in ort.get_available_providers()
    except Exception:
        return False


def select_device(preference: str = "auto") -> str:
    """Resolves the torch/ultralytics device string.

    "auto" prefers CUDA, then Apple MPS (the Mac mini this ships on), then CPU.
    """
    if preference and preference != "auto":
        return preference
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"
