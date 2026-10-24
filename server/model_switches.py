"""Atomic local model switches shared by the API and live inference worker."""

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Mapping


CONTROL_KEYS = (
    "person_detector",
    "pose",
    "face",
    "products",
    "reid",
    "rtmpose",
    "demographics",
    "rfdetr",
)
DEFAULT_CONTROLS = {key: True for key in CONTROL_KEYS}
# The primary live profile uses RTMPose for foot/keypoint refinement. The
# standalone YOLO pose model is intentionally disabled to avoid duplicate pose
# inference; operators may turn it on for a future validated comparison.
DEFAULT_CONTROLS["pose"] = False
DEFAULT_CONTROLS["demographics"] = False
DEFAULT_CONTROLS["rfdetr"] = False
DEFAULT_PATH = Path(__file__).resolve().parents[1] / "local-runtime" / "model-switches.json"
_LOCK = Lock()
_CACHE_PATH = None
_CACHE_MTIME = None
_CACHE_CONTROLS = dict(DEFAULT_CONTROLS)


def controls_path() -> str:
    return os.environ.get("EDGESIGHT_MODEL_SWITCHES_PATH") or str(DEFAULT_PATH)


def read_controls(path: str | os.PathLike[str] | None = None) -> dict[str, bool]:
    """Read saved controls; missing, malformed, or unknown values fail safely to defaults."""
    global _CACHE_PATH, _CACHE_MTIME, _CACHE_CONTROLS
    target = str(path or controls_path())
    try:
        mtime = os.stat(target).st_mtime_ns
    except OSError:
        mtime = None
    with _LOCK:
        if target == _CACHE_PATH and mtime == _CACHE_MTIME:
            return dict(_CACHE_CONTROLS)
        values = dict(DEFAULT_CONTROLS)
        if mtime is not None:
            try:
                with open(target, encoding="utf-8") as stream:
                    payload: Any = json.load(stream)
                saved = payload.get("controls", payload) if isinstance(payload, dict) else {}
                if isinstance(saved, dict):
                    for key in CONTROL_KEYS:
                        if isinstance(saved.get(key), bool):
                            values[key] = saved[key]
            except (OSError, ValueError, TypeError):
                pass
        _CACHE_PATH, _CACHE_MTIME, _CACHE_CONTROLS = target, mtime, values
        return dict(values)


def write_control(key: str, enabled: bool, path: str | os.PathLike[str] | None = None) -> dict[str, bool]:
    if key not in DEFAULT_CONTROLS:
        raise KeyError(key)
    target = Path(path or controls_path())
    values = read_controls(target)
    values[key] = bool(enabled)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    with _LOCK:
        temporary.write_text(json.dumps({"controls": values}, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, target)
        global _CACHE_PATH, _CACHE_MTIME, _CACHE_CONTROLS
        _CACHE_PATH = None
    return read_controls(target)


def active_model_names(loaded: Mapping[str, bool], controls: Mapping[str, bool]) -> list[str]:
    """List loaded models whose operator switch is on, not merely present on disk."""
    return [name for name, is_loaded in loaded.items() if is_loaded and controls.get(name, False)]
