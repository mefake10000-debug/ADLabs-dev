import unittest

from src.main import EdgePipeline


class TestEnabledCameraConfig(unittest.TestCase):
    def test_disabled_camera_is_not_initialized(self):
        pipeline = EdgePipeline.__new__(EdgePipeline)
        pipeline.cameras_cfg = {"cameras": [
            {"id": "primary", "enabled": True},
            {"id": "disabled", "enabled": False},
        ]}
        pipeline.camera_contexts = {}
        pipeline._build_camera_context = lambda camera: {"camera_id": camera["id"]}

        pipeline._init_cameras()

        self.assertEqual(list(pipeline.camera_contexts), ["primary"])


if __name__ == "__main__":
    unittest.main()
