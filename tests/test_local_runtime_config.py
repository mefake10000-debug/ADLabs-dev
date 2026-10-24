import unittest
from pathlib import Path

import yaml


class LocalRuntimeConfigTests(unittest.TestCase):
    def test_native_worker_uses_the_store_served_by_this_checkout(self):
        config_path = Path(__file__).parents[1] / "local-runtime" / "pipeline.native.yaml"
        config = yaml.safe_load(config_path.read_text())
        self.assertEqual(config["storage"]["db_path"], "data/storage/edgesight.db")

    def test_native_worker_telemetry_uses_the_local_dashboard_api(self):
        config_path = Path(__file__).parents[1] / "local-runtime" / "pipeline.native.yaml"
        config = yaml.safe_load(config_path.read_text())
        self.assertEqual(
            config["telemetry"]["local_endpoint"],
            "http://127.0.0.1:8001/api/v1/telemetry",
        )

    def test_native_profile_keeps_only_selected_role_models_enabled(self):
        root = Path(__file__).parents[1]
        config = yaml.safe_load((root / "local-runtime" / "pipeline.native.yaml").read_text())
        switches = yaml.safe_load((root / "local-runtime" / "model-switches.json").read_text())[
            "controls"
        ]
        self.assertFalse(config["models"]["pose"]["enabled"])
        self.assertFalse(config["models"]["face"]["enabled"])
        self.assertFalse(config["models"]["head_pose"]["enabled"])
        self.assertEqual(config["models"]["products"]["backend"], "yoloe")
        self.assertFalse(switches["face"])

    def test_native_fast_profile_skips_detector_frames_but_keeps_each_frame_display(self):
        config_path = Path(__file__).parents[1] / "local-runtime" / "pipeline.native.yaml"
        config = yaml.safe_load(config_path.read_text())
        self.assertEqual(config["performance"]["infer_every_n"], 3)
        self.assertEqual(config["performance"]["display_every_n"], 1)
        self.assertEqual(config["perception"]["infer_every_n"], 3)

    def test_native_profile_prioritizes_people_and_bounds_enrichment(self):
        root = Path(__file__).parents[1]
        config = yaml.safe_load((root / "local-runtime" / "pipeline.native.yaml").read_text())
        switches = yaml.safe_load((root / "local-runtime" / "model-switches.json").read_text())["controls"]
        self.assertEqual(config["performance"]["imgsz"], 512)
        self.assertEqual(config["perception"]["confidence_threshold"], 0.20)
        self.assertEqual(config["tracking"]["track_thresh"], 0.25)
        self.assertEqual(config["perception"]["min_height"], 55)
        self.assertEqual(config["perception"]["min_area"], 1200)
        self.assertEqual(config["models"]["slow_tier"]["parallel_model_workers"], 1)
        self.assertEqual(config["models"]["slow_tier"]["interval_frames"], 32)
        self.assertEqual(config["models"]["enrichment_threads"], 1)
        self.assertEqual(config["models"]["reid"]["interval_frames"], 32)
        self.assertTrue(switches["products"])
        self.assertTrue(switches["reid"])
        self.assertTrue(switches["rtmpose"])


if __name__ == "__main__":
    unittest.main()
