import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from server.model_evaluation import read_model_evaluation


def valid_report(evaluated_at=None):
    return {
        "schema_version": 1,
        "evaluated_at": (evaluated_at or datetime.now(timezone.utc)).isoformat(),
        "model": "YOLO26s",
        "clip": "entrance-labeled-v1.mp4",
        "config_id": "pilot-balanced-512",
        "dataset": {"name": "entrance labels v1", "labeled_frames": 120, "ground_truth_people": 340},
        "metrics": {"precision": 0.91, "recall": 0.82, "f1": 0.86, "count_mae": 0.7},
    }


class ModelEvaluationTests(unittest.TestCase):
    def test_missing_report_is_explicitly_not_measured_without_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            result = read_model_evaluation(os.path.join(directory, "missing.json"))
        self.assertEqual(result["status"], "not_measured")
        self.assertIsNone(result["metrics"])

    def test_stale_report_is_not_exposed_as_current_measurement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "report.json")
            with open(path, "w") as stream:
                json.dump(valid_report(datetime.now(timezone.utc) - timedelta(days=8)), stream)
            result = read_model_evaluation(path)
        self.assertEqual(result["status"], "not_measured")
        self.assertIn("stale", result["reason"])
        self.assertIsNone(result["metrics"])

    def test_valid_labeled_report_exposes_metrics_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "report.json")
            with open(path, "w") as stream:
                json.dump(valid_report(), stream)
            result = read_model_evaluation(path)
        self.assertEqual(result["status"], "measured")
        self.assertEqual(result["metrics"]["recall"], 0.82)
        self.assertEqual(result["provenance"]["clip"], "entrance-labeled-v1.mp4")

    def test_report_without_ground_truth_provenance_is_rejected(self):
        report = valid_report()
        report["dataset"]["ground_truth_people"] = 0
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "report.json")
            with open(path, "w") as stream:
                json.dump(report, stream)
            result = read_model_evaluation(path)
        self.assertEqual(result["status"], "not_measured")
        self.assertIsNone(result["metrics"])


if __name__ == "__main__":
    unittest.main()
