import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


class ComposeLoader(yaml.SafeLoader):
    pass


ComposeLoader.add_constructor("!override", lambda loader, node: loader.construct_sequence(node))


class LocalComposeProfileTests(unittest.TestCase):
    def test_edge_analyzer_has_a_four_cpu_ceiling_without_capping_other_services(self):
        compose = yaml.load((ROOT / "docker-compose.yml").read_text(), Loader=ComposeLoader)
        services = compose["services"]
        self.assertEqual(services["edge-analyzer"].get("cpus"), 4.0)
        self.assertNotIn("cpus", services["cloud-dashboard"])
        self.assertNotIn("cpus", services["rtsp-simulator"])

    def test_override_uses_this_checkout_and_live_native_profile(self):
        compose = yaml.load((ROOT / "compose.local-models.yaml").read_text(), Loader=ComposeLoader)
        edge = compose["services"]["edge-analyzer"]
        self.assertIn("./server:/app/server:ro", edge["volumes"])
        self.assertEqual(edge["environment"]["PYTHONPATH"], "/app:/app/vendor/MiVOLO")
        self.assertTrue(any("/Desktop/ad-labs-project/repos/ADLabs-dev/models:/Users/" in mount for mount in edge["volumes"]))
        self.assertIn("./models:/app/models", edge["volumes"])
        self.assertIn("./data/storage:/app/data/storage", edge["volumes"])
        self.assertEqual(edge["environment"]["PIPELINE_CONFIG"], "/app/configs/pipeline.native.yaml")
        self.assertEqual(edge["environment"]["CAMERAS_CONFIG"], "/app/configs/cameras.yaml")
        self.assertEqual(edge["environment"]["EDGESIGHT_MODEL_SWITCHES_PATH"], "/app/configs/model-switches.json")
        self.assertEqual(edge["environment"]["EDGE_PERF_MODE"], "fast")
        self.assertEqual(edge["environment"]["EDGE_ENRICHMENT"], "1")
        self.assertEqual(edge["environment"]["ENABLE_RTMPOSE"], "1")
        self.assertEqual(edge["environment"]["RTMPOSE_EVERY_N"], "8")
        self.assertEqual(edge["environment"]["OVERLAY_BOX_STYLE"], "aabb")
        self.assertEqual(edge["environment"]["EDGESIGHT_DETECT_MODEL"], "models/yolo26n.pt")
        self.assertEqual(edge["environment"]["SAMPLE_VIDEOS_EXTRA_DIRS"], "/app/data/test-footage")
        self.assertIn("./local-runtime:/app/configs:ro", edge["volumes"])
        self.assertNotIn("./local-runtime/model-switches.json:/app/configs/model-switches.json", edge["volumes"])
        self.assertNotIn("/Users/nishantparihar/Desktop/ad labs/", "\n".join(edge["volumes"]))
        dashboard = compose["services"]["cloud-dashboard"]
        self.assertEqual(dashboard["ports"], ["8001:8000"])
        self.assertIn("./local-runtime:/app/configs", dashboard["volumes"])
        self.assertNotIn("./local-runtime:/app/configs:ro", dashboard["volumes"])
        self.assertNotIn("./local-runtime/model-switches.json:/app/configs/model-switches.json", dashboard["volumes"])
        self.assertEqual(dashboard["environment"]["EDGESIGHT_MODEL_SWITCHES_PATH"], "/app/configs/model-switches.json")
        self.assertIn("./models:/app/models:ro", dashboard["volumes"])

    def test_local_compose_mounts_private_desktop_test_footage_read_only(self):
        compose = yaml.load((ROOT / "compose.local-models.yaml").read_text(), Loader=ComposeLoader)
        edge = compose["services"]["edge-analyzer"]
        self.assertIn(
            "/Users/nishantparihar/Desktop/ad-labs-project/test-footage:/app/data/test-footage:ro",
            edge["volumes"],
        )
        self.assertEqual(edge["environment"]["EDGE_PERF_MODE"], "fast")

    def test_local_camera_video_path_is_available_under_container_mount(self):
        cameras = yaml.safe_load((ROOT / "local-runtime" / "cameras.yaml").read_text())
        source = Path(cameras["cameras"][0]["source"])
        if not source.is_absolute():
            self.assertTrue((ROOT / source).is_file())
            return

        compose = yaml.load((ROOT / "compose.local-models.yaml").read_text(), Loader=ComposeLoader)
        volumes = compose["services"]["edge-analyzer"]["volumes"]
        for mount in volumes:
            host_path, container_path, *_ = mount.split(":")
            container_root = Path(container_path)
            try:
                relative_source = source.relative_to(container_root)
            except ValueError:
                continue
            self.assertTrue((Path(host_path) / relative_source).is_file())
            return
        self.fail(f"No edge-analyzer volume mount contains camera source {source}")

    def test_edge_image_does_not_reinstall_cpu_torch_from_pypi(self):
        dockerfile = (ROOT / "docker" / "Dockerfile.edge").read_text()
        self.assertIn("sed -E '/^(torch|torchvision)==/d'", dockerfile)
        self.assertIn("pip install --no-cache-dir -r /tmp/requirements-edge-docker.txt", dockerfile)


if __name__ == "__main__":
    unittest.main()
