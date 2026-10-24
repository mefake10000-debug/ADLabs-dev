import unittest

from src.main import filter_camera_config, main


class WorkerCameraScopeTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "cameras": [
                {"id": "front", "enabled": True},
                {"id": "checkout", "enabled": True},
                {"id": "disabled", "enabled": False},
            ]
        }

    def test_filter_keeps_only_requested_enabled_cameras(self):
        self.assertEqual(
            filter_camera_config(self.config, ["checkout"]),
            {"cameras": [{"id": "checkout", "enabled": True}]},
        )

    def test_empty_unknown_and_disabled_selection_are_rejected(self):
        for selected in ([], ["missing"], ["disabled"]):
            with self.subTest(selected=selected):
                with self.assertRaises(ValueError):
                    filter_camera_config(self.config, selected)

    def test_native_cli_requires_explicit_camera_selection(self):
        with self.assertRaises(SystemExit) as exit_info:
            main([])
        self.assertEqual(exit_info.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
