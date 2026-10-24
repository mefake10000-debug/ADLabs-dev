"""Operator model switches are atomic and default every capability to enabled."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from server.model_switches import CONTROL_KEYS, active_model_names, read_controls, write_control


class ModelSwitchTests(unittest.TestCase):
    def test_missing_switch_file_disables_duplicate_pose_path_but_keeps_others_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            controls = read_controls(Path(directory) / "switches.json")
        self.assertEqual(set(controls), set(CONTROL_KEYS))
        self.assertFalse(controls["pose"])
        self.assertFalse(controls["demographics"])
        self.assertFalse(controls["rfdetr"])
        self.assertTrue(all(value for key, value in controls.items() if key not in ("pose", "demographics", "rfdetr")))

    def test_one_model_can_be_paused_without_turning_off_its_peers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "switches.json"
            controls = write_control("products", False, path)
            self.assertFalse(controls["products"])
            for model in ("person_detector", "face", "reid", "rtmpose"):
                self.assertTrue(controls[model])
            self.assertFalse(controls["demographics"])
            self.assertFalse(controls["rfdetr"])

    def test_unknown_model_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KeyError):
                write_control("nonsense", False, Path(directory) / "switches.json")

    def test_runtime_active_list_excludes_loaded_models_whose_switch_is_off(self):
        loaded = {"products": True, "reid": True, "rtmpose": True}
        controls = {"products": False, "reid": False, "rtmpose": False}
        self.assertEqual(active_model_names(loaded, controls), [])


if __name__ == "__main__":
    unittest.main()
