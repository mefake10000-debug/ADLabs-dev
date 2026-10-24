"""Read-only, provenance-checked ground-truth evaluation summary."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


MAX_AGE_DAYS = 7
METRIC_KEYS = ("precision", "recall", "f1", "count_mae")


def _not_measured(reason: str) -> Dict[str, Any]:
    return {"status": "not_measured", "reason": reason, "metrics": None, "provenance": None}


def _parse_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def read_model_evaluation(path: str | Path, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Expose metrics only from a recent report with labeled data and provenance.

    Expected JSON contract is documented in docs/models/adding-models.md. Detector
    confidence scores and unlabelled demo clips intentionally cannot satisfy it.
    """
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _not_measured("No labeled evaluation report is available.")
    except (OSError, json.JSONDecodeError):
        return _not_measured("The evaluation report is unreadable.")
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        return _not_measured("The evaluation report does not match the supported schema.")

    evaluated_at = _parse_time(report.get("evaluated_at"))
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if evaluated_at is None or evaluated_at > current_time:
        return _not_measured("The evaluation timestamp is missing or invalid.")
    age_seconds = (current_time - evaluated_at).total_seconds()
    if age_seconds > MAX_AGE_DAYS * 86400:
        return _not_measured("The labeled evaluation report is stale.")

    dataset = report.get("dataset")
    metrics = report.get("metrics")
    if not isinstance(dataset, dict) or not isinstance(metrics, dict):
        return _not_measured("Ground-truth labels or measured metrics are missing.")
    try:
        labeled_frames = int(dataset.get("labeled_frames", 0))
        ground_truth_people = int(dataset.get("ground_truth_people", 0))
    except (TypeError, ValueError):
        return _not_measured("Ground-truth label counts are invalid.")
    if labeled_frames <= 0 or ground_truth_people <= 0:
        return _not_measured("The report contains no labeled frames or people.")

    model = report.get("model")
    clip = report.get("clip")
    config_id = report.get("config_id")
    dataset_name = dataset.get("name")
    if not all(isinstance(value, str) and value.strip() for value in (model, clip, config_id, dataset_name)):
        return _not_measured("Model, clip, dataset, and configuration provenance are required.")

    clean_metrics: Dict[str, float] = {}
    for key in METRIC_KEYS:
        value = metrics.get(key)
        try:
            number = float(value)
        except (TypeError, ValueError):
            return _not_measured("One or more required ground-truth metrics are missing.")
        if not math.isfinite(number) or number < 0 or (key != "count_mae" and number > 1):
            return _not_measured("One or more ground-truth metrics are outside valid bounds.")
        clean_metrics[key] = number

    return {
        "status": "measured",
        "reason": None,
        "evaluated_at": evaluated_at.isoformat(),
        "age_days": round(age_seconds / 86400, 2),
        "metrics": clean_metrics,
        "provenance": {
            "model": model,
            "clip": clip,
            "config_id": config_id,
            "dataset": dataset_name,
            "labeled_frames": labeled_frames,
            "ground_truth_people": ground_truth_people,
        },
    }
