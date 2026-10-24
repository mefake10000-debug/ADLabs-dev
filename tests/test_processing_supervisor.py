import json
import os
import subprocess
import sys
import tempfile
import time
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock, patch

from src.runtime.supervisor import ProcessingSupervisor, make_handler, notify_worker_ready


class ProcessingSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.video = self.root / "camera.mp4"
        self.video.write_bytes(b"test fixture")
        self.config = self.root / "cameras.yaml"
        self.config.write_text(
            "cameras:\n"
            "  - id: cam_a\n"
            f"    source: {self.video}\n"
            "    enabled: true\n"
            "  - id: cam_b\n"
            f"    source: {self.video}\n"
            "    enabled: true\n"
            "  - id: cam_disabled\n"
            f"    source: {self.video}\n"
            "    enabled: false\n"
        )
        self.pipeline_config = self.root / "pipeline.yaml"
        self.weights = self.root / "person.pt"
        self.weights.write_bytes(b"test-only placeholder")
        self.pipeline_config.write_text(
            "perception:\n"
            "  require_model: true\n"
            f"  model_name: [{self.weights}]\n"
        )
        self.state_dir = self.root / "state"
        self.process = Mock()
        self.process.pid = 412
        self.process.poll.return_value = None
        self.popen = Mock(return_value=self.process)
        self.supervisor = ProcessingSupervisor(
            camera_config_path=str(self.config),
            state_dir=str(self.state_dir),
            control_key="test-secret",
            pipeline_config_path=str(self.pipeline_config),
            popen_factory=self.popen,
            shutdown_timeout_seconds=0.01,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_status_starts_off_without_creating_worker(self):
        self.assertEqual(self.supervisor.status()["state"], "OFF")
        self.popen.assert_not_called()

    def test_supervisor_restart_marks_existing_snapshot_stale_without_erasing_counts(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        live_path = self.state_dir / "live.json"
        live_path.write_text(json.dumps({"cameras": [{"counts": {"entries": 8}}]}))
        restarted = ProcessingSupervisor(
            camera_config_path=str(self.config),
            state_dir=str(self.state_dir),
            control_key="test-secret",
            pipeline_config_path=str(self.pipeline_config),
            popen_factory=self.popen,
        )
        live = json.loads(live_path.read_text())
        self.assertEqual(restarted.status()["state"], "OFF")
        self.assertEqual(live["cameras"][0]["counts"], {"entries": 8})
        self.assertEqual(live["processing"]["state"], "OFF")
        self.assertTrue(live["processing"]["stale"])

    def test_worker_creation_failure_is_reported_without_retry(self):
        failed = ProcessingSupervisor(
            camera_config_path=str(self.config),
            state_dir=str(self.state_dir),
            control_key="test-secret",
            pipeline_config_path=str(self.pipeline_config),
            popen_factory=Mock(side_effect=OSError("missing python worker")),
        )
        status = failed.start(["cam_a"])
        self.assertEqual(status["state"], "ERROR")
        self.assertIn("missing python worker", status["error"])

    def test_stop_during_starting_terminates_worker_and_confirms_off(self):
        self.supervisor.start(["cam_a"])
        self.process.wait.return_value = 0
        status = self.supervisor.stop()
        self.assertEqual(status["state"], "OFF")
        self.process.terminate.assert_called_once()

    def test_hung_worker_is_killed_after_bounded_stop_wait(self):
        self.supervisor.start(["cam_a"])
        self.process.wait.side_effect = [subprocess.TimeoutExpired("worker", 0.01), 0]
        status = self.supervisor.stop()
        self.assertEqual(status["state"], "OFF")
        self.assertIn("forced stop", status["error"])
        self.process.kill.assert_called_once()

    def test_worker_still_alive_after_kill_returns_error_and_keeps_handle(self):
        self.supervisor.start(["cam_a"])
        self.process.wait.side_effect = [
            subprocess.TimeoutExpired("worker", 0.01),
            subprocess.TimeoutExpired("worker", 2.0),
        ]

        status = self.supervisor.stop()

        self.assertEqual(status["state"], "ERROR")
        self.assertEqual(status["worker_pid"], 412)
        self.assertIn("did not exit after forced stop", status["error"])
        live = json.loads((self.state_dir / "live.json").read_text())
        self.assertEqual(live["processing"]["state"], "ERROR")
        self.assertTrue(live["processing"]["stale"])
        self.assertIs(self.supervisor._child, self.process)

    def test_start_accepts_only_enabled_configured_cameras(self):
        status = self.supervisor.start(["cam_a"])
        self.assertEqual(status["state"], "STARTING")
        self.assertEqual(status["camera_ids"], ["cam_a"])
        command = self.popen.call_args.args[0]
        self.assertIn("--camera-ids", command)
        self.assertEqual(command[-1], "cam_a")

    def test_start_rejects_unknown_disabled_empty_or_duplicate_camera_ids(self):
        for camera_ids in ([], ["missing"], ["cam_disabled"], ["cam_a", "cam_a"]):
            with self.subTest(camera_ids=camera_ids):
                with self.assertRaises(ValueError):
                    self.supervisor.start(camera_ids)
        self.popen.assert_not_called()

    def test_start_rejects_missing_required_person_weights_before_spawning(self):
        self.pipeline_config.write_text(
            "perception:\n"
            "  require_model: true\n"
            "  model_name: [missing-person.pt]\n"
        )
        with self.assertRaisesRegex(ValueError, "Required person detector weights are missing"):
            self.supervisor.start(["cam_a"])
        self.popen.assert_not_called()

    def test_start_is_idempotent_for_same_scope_and_rejects_scope_change(self):
        first = self.supervisor.start(["cam_a"])
        second = self.supervisor.start(["cam_a"])
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual(self.popen.call_count, 1)
        with self.assertRaises(RuntimeError):
            self.supervisor.start(["cam_b"])

    def test_ready_requires_matching_session_and_process_exit_becomes_error(self):
        started = self.supervisor.start(["cam_a"])
        with self.assertRaises(ValueError):
            self.supervisor.mark_ready("wrong-session")
        running = self.supervisor.mark_ready(started["session_id"])
        self.assertEqual(running["state"], "RUNNING")
        self.process.poll.return_value = 2
        failed = self.supervisor.status()
        self.assertEqual(failed["state"], "ERROR")
        self.assertIn("exit code 2", failed["error"])
        live = json.loads((self.state_dir / "live.json").read_text())
        self.assertEqual(live["processing"]["state"], "ERROR")
        self.assertTrue(live["processing"]["stale"])

    def test_running_worker_is_fresh_only_when_selected_camera_has_recent_frame(self):
        started = self.supervisor.start(["cam_a"])
        self.supervisor.mark_ready(started["session_id"])
        self.assertFalse(self.supervisor.status()["fresh"])
        self.state_dir.mkdir(parents=True, exist_ok=True)
        (self.state_dir / "live.json").write_text(json.dumps({
            "cameras": [{
                "camera_id": "cam_a",
                "session_id": started["session_id"],
                "last_frame_received_epoch": time.time(),
            }]
        }))
        self.assertTrue(self.supervisor.status()["fresh"])

    def test_internal_status_requires_control_secret_and_stop_is_idempotent(self):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.supervisor, "test-secret"))
        except PermissionError as error:
            self.skipTest(f"sandbox disallows loopback bind: {error}")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/internal/processing/status"
        try:
            with self.assertRaises(HTTPError) as denied:
                urlopen(url, timeout=2)
            self.assertEqual(denied.exception.code, 401)
            request = Request(url, headers={"X-Control-Key": "test-secret"})
            with urlopen(request, timeout=2) as response:
                self.assertEqual(json.loads(response.read())["state"], "OFF")
            self.assertEqual(self.supervisor.stop()["state"], "OFF")
            self.assertEqual(self.supervisor.stop()["state"], "OFF")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_stop_preserves_rollups_and_marks_live_snapshot_off_and_stale(self):
        started = self.supervisor.start(["cam_a"])
        self.supervisor.mark_ready(started["session_id"])
        self.state_dir.mkdir(parents=True, exist_ok=True)
        live_path = self.state_dir / "live.json"
        live_path.write_text(json.dumps({"cameras": [{"occupancy": 7}], "rollups": ["keep"]}))

        self.process.wait.return_value = 0
        stopped = self.supervisor.stop()
        self.assertEqual(stopped["state"], "OFF")
        live = json.loads(live_path.read_text())
        self.assertEqual(live["cameras"], [{"occupancy": 7}])
        self.assertEqual(live["rollups"], ["keep"])
        self.assertEqual(live["processing"]["state"], "OFF")
        self.assertTrue(live["processing"]["stale"])
        self.process.terminate.assert_called_once()


class SupervisorImportIsolationTests(unittest.TestCase):
    def test_import_does_not_import_video_or_model_libraries(self):
        command = [
            sys.executable,
            "-c",
            "import sys; import src.runtime.supervisor; "
            "assert 'torch' not in sys.modules; assert 'cv2' not in sys.modules",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_worker_ready_notification_is_bound_to_session_and_internal_key(self):
        with patch.dict(os.environ, {
            "SUPERVISOR_URL": "http://127.0.0.1:8001",
            "PROCESSING_SESSION_ID": "session-a",
            "PROCESSING_CONTROL_KEY": "internal-secret",
        }), patch("src.runtime.supervisor.urlopen") as upstream:
            notify_worker_ready()
        request = upstream.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8001/internal/processing/ready")
        self.assertEqual(request.get_header("X-control-key"), "internal-secret")
        self.assertEqual(json.loads(request.data), {"session_id": "session-a"})


class DockerOffByDefaultTests(unittest.TestCase):
    def test_compose_default_starts_model_free_supervisor_and_keeps_simulator_opt_in(self):
        import yaml

        compose = yaml.safe_load(Path("docker-compose.yml").read_text())
        services = compose["services"]
        self.assertIn("simulator", services["rtsp-simulator"].get("profiles", []))
        self.assertNotIn("rtsp-simulator", services["edge-analyzer"].get("depends_on", []))
        self.assertEqual(services["edge-analyzer"]["build"]["dockerfile"], "docker/Dockerfile.edge")
        self.assertNotIn("command", services["edge-analyzer"])
        self.assertEqual(services["edge-analyzer"]["restart"], "unless-stopped")
        model_mounts = [mount for mount in services["edge-analyzer"]["volumes"] if "models:" in mount or "weights:" in mount]
        self.assertTrue(model_mounts)
        self.assertTrue(all(mount.endswith(":ro") for mount in model_mounts))
        self.assertTrue(all(port.startswith("127.0.0.1:") for port in services["cloud-dashboard"]["ports"]))

    def test_edge_image_entrypoint_does_not_start_main_pipeline(self):
        dockerfile = Path("docker/Dockerfile.edge").read_text()
        self.assertIn('CMD ["python", "-m", "src.runtime.supervisor"]', dockerfile)
        self.assertNotIn('CMD ["python", "-m", "src.main"]', dockerfile)


if __name__ == "__main__":
    unittest.main()
