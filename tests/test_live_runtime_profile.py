"""The native live launcher keeps the verified model stack enabled with bounded cadence."""
from __future__ import annotations

import importlib
import unittest


class LiveRuntimeProfileTests(unittest.TestCase):
    def test_live_profile_enables_models_parallelizes_slow_tier_and_uses_shared_database(self):
        # Resolve lazily so the red test fails as an assertion when the profile is absent.
        try:
            module = importlib.import_module("src.perception.live_runtime")
        except ModuleNotFoundError:
            module = None
        build = getattr(module, "build_live_profile", None) if module else None
        self.assertTrue(callable(build), "native live profile must keep the edge model stack scheduled")

        base = {
            "performance": {"mode": "fast", "max_cameras": 2},
            "perception": {"model_name": "models/yolo26n.pt", "imgsz": 320},
            "storage": {"db_path": "old.db"},
            "models": {
                "enabled": False,
                "slow_tier": {"interval_frames": 2, "parallel_model_workers": 1},
                "pose": {"enabled": False},
                "face": {"enabled": False},
                "demographics": {"enabled": False},
                "head_pose": {"enabled": False},
                "products": {"enabled": False},
                "reid": {"enabled": False},
            },
        }
        profile = build(base, shared_db_path="/shared/storage/edgesight.db")
        self.assertEqual(profile["performance"]["mode"], "quality")
        self.assertEqual(profile["performance"]["max_cameras"], 1)
        self.assertEqual(profile["perception"]["model_name"], "models/yolo26s.pt")
        self.assertEqual(profile["storage"]["db_path"], "/shared/storage/edgesight.db")
        self.assertTrue(profile["models"]["enabled"])
        self.assertFalse(profile["models"]["pose"]["enabled"], "RTMPose is the single active pose path")
        self.assertEqual(profile["models"]["products"]["backend"], "yoloe")
        self.assertTrue(all(profile["models"][name]["enabled"] for name in ("face", "demographics", "head_pose", "products", "reid")))
        self.assertEqual(profile["models"]["slow_tier"]["parallel_model_workers"], 3)
        self.assertEqual(profile["models"]["slow_tier"]["interval_frames"], 16)
        self.assertFalse(profile["cross_camera_fusion"]["enabled"])
        self.assertFalse(base["models"]["enabled"], "profile builder must not mutate its source config")


if __name__ == "__main__":
    unittest.main()
