import ast
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from src.storage.local_buffer import LocalBuffer
from src.telemetry.exporter import TelemetryExporter
import server.app as api

def event():
    return dict(store_id='hardening-store', device_id='edge-1', camera_id='cam-1', wire_id='entrance', track_id=1, direction='in', event_timestamp='2026-10-25 00:00:00')

class DurableDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / 'edge.db')
        self.buffer = LocalBuffer(self.db)

    def test_identity_survives_restart(self):
        self.buffer.save_event(event())
        self.buffer.save_event(event())
        rows = self.buffer.get_unexported_events()
        self.assertTrue(rows[0].get('record_id'))
        self.assertNotEqual(rows[0]['record_id'], rows[1]['record_id'])
        self.assertEqual(rows, LocalBuffer(self.db).get_unexported_events())

    def test_partial_ack_preserves_pending(self):
        self.buffer.save_event(event())
        self.buffer.save_event(event())
        rows = self.buffer.get_unexported_events()
        response = Mock(status_code=200)
        response.json.return_value = {'accepted_record_ids': [rows[0].get('record_id')]}
        exporter = TelemetryExporter(self.buffer, 'http://receiver/api/v1/telemetry')
        with patch('src.telemetry.exporter.requests.post', return_value=response):
            self.assertEqual(exporter.flush_events_once(), 1)
        self.assertEqual([r['id'] for r in self.buffer.get_unexported_events()], [rows[1]['id']])

    def test_lost_response_retry_and_conflicting_id(self):
        with patch.object(api, 'DB_PATH', str(Path(self.temp.name) / 'receiver.db')):
            api.init_db()
            client = TestClient(api.app)
            payload = dict(batch_size=1, events=[dict(event(), record_id='stable-event-1')], exported_at=time.time())
            for _ in range(2):
                response = client.post('/api/v1/telemetry/events', json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json().get('accepted_record_ids'), ['stable-event-1'])
            with sqlite3.connect(api.DB_PATH) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM telemetry_events').fetchone()[0], 1)
            payload['events'][0]['direction'] = 'out'
            self.assertEqual(client.post('/api/v1/telemetry/events', json=payload).status_code, 409)

    def test_maintenance_preserves_pending(self):
        self.buffer.save_event(event())
        self.buffer.save_event(event())
        self.buffer.mark_events_as_exported([1])
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE crossing_events SET created_at='2000-01-01 00:00:00'")
        self.buffer.maintenance(retention_days=7)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT id FROM crossing_events').fetchall(), [(2,)])
        self.assertEqual(self.buffer.backlog_stats()['pending_records'], 1)

    def test_shutdown_interrupts_interval(self):
        exporter = TelemetryExporter(self.buffer, 'http://receiver', push_interval_seconds=120)
        exporter.start()
        thread = exporter.thread
        exporter.stop()
        self.assertFalse(thread.is_alive())

class PipelineIntegrityTests(unittest.TestCase):
    def test_no_shadowed_methods(self):
        tree = ast.parse(Path('src/main.py').read_text())
        pipeline = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'EdgePipeline')
        names = [n.name for n in pipeline.body if isinstance(n, ast.FunctionDef)]
        self.assertEqual(len(names), len(set(names)))

class ReadinessTests(unittest.TestCase):
    def test_readiness_rejects_stale_missing_future_and_low_disk(self):
        from server.runtime_readiness import assess_readiness
        for snapshot in (None, {'frame_time': 50}, {'frame_time': 150}):
            self.assertFalse(assess_readiness(snapshot, now=100, free_bytes=10**10)['ready'])
        self.assertTrue(assess_readiness({'frame_time': 99, 'infer_fps': 2}, now=100, free_bytes=10**10)['ready'])
        self.assertFalse(assess_readiness({'frame_time': 99, 'infer_fps': 2}, now=100, free_bytes=1)['ready'])
        self.assertFalse(assess_readiness({'frame_time': 99, 'infer_fps': 0}, now=100, free_bytes=10**10)['ready'])

    def test_ready_endpoint_is_separate_from_liveness(self):
        client = TestClient(api.app)
        with patch.object(api, '_read_live_snapshot', return_value=None):
            self.assertEqual(client.get('/health').status_code, 200)
            response = client.get('/ready')
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()['ready'])

class OperatorAccessTests(unittest.TestCase):
    def test_operator_credentials_protect_video_and_write_roles(self):
        env = {'EDGESIGHT_OPERATOR_USER': 'owner', 'EDGESIGHT_OPERATOR_PASSWORD': 'secret-password',
               'EDGESIGHT_VIEWER_USER': 'viewer', 'EDGESIGHT_VIEWER_PASSWORD': 'viewer-password'}
        client = TestClient(api.app)
        with patch.dict(os.environ, env):
            self.assertEqual(client.get('/api/v1/cameras').status_code, 401)
            self.assertEqual(client.get('/').status_code, 401)
            self.assertEqual(client.get('/api/v1/cameras', auth=('owner', 'wrong')).status_code, 401)
            self.assertEqual(client.get('/api/v1/cameras', auth=('viewer', 'viewer-password')).status_code, 200)
            self.assertEqual(client.post('/api/v1/metrics/reset', auth=('viewer', 'viewer-password'), json={}).status_code, 403)
            self.assertEqual(client.get('/health').status_code, 200)

    def test_secure_mode_requires_configuration(self):
        client = TestClient(api.app)
        with patch.dict(os.environ, {'EDGESIGHT_SECURE_MODE': '1', 'EDGESIGHT_OPERATOR_USER': '', 'EDGESIGHT_OPERATOR_PASSWORD': ''}):
            self.assertEqual(client.get('/api/v1/cameras').status_code, 503)

    def test_device_secret_never_appears_in_html(self):
        client = TestClient(api.app)
        with patch.object(api, 'API_KEY', 'unique-device-secret'):
            self.assertNotIn('unique-device-secret', client.get('/').text)

class AccessAndRecoveryRegressionTests(unittest.TestCase):
    def test_cross_origin_operator_write_is_rejected(self):
        env = {'EDGESIGHT_OPERATOR_USER': 'owner', 'EDGESIGHT_OPERATOR_PASSWORD': 'secret-password'}
        with patch.dict(os.environ, env):
            response = TestClient(api.app).post('/api/v1/metrics/reset', auth=('owner', 'secret-password'), headers={'Origin': 'https://attacker.example'})
        self.assertEqual(response.status_code, 403)

    def test_camera_snapshot_readiness_ignores_store_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            import json
            db = str(Path(directory) / 'api.db')
            live = Path(directory) / 'live'
            live.mkdir()
            (live / 'cam-1.json').write_text(json.dumps({'camera_id': 'cam-1', 'frame_time': time.time(), 'infer_fps': 2}))
            (live / 'store.json').write_text(json.dumps({'timestamp': '2026-10-25 00:00:00', 'infer_fps': 2}))
            with patch.object(api, 'DB_PATH', db):
                api.init_db()
                response = TestClient(api.app).get('/ready')
            self.assertEqual(response.status_code, 200)

    def test_successful_operator_write_is_audited_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {'EDGESIGHT_OPERATOR_USER': 'owner', 'EDGESIGHT_OPERATOR_PASSWORD': 'secret-password'}
            with patch.object(api, 'DB_PATH', str(Path(directory) / 'api.db')), patch.dict(os.environ, env):
                api.init_db()
                response = TestClient(api.app).post('/api/v1/metrics/reset', auth=('owner', 'secret-password'))
                self.assertEqual(response.status_code, 200)
                with sqlite3.connect(api.DB_PATH) as conn:
                    row = conn.execute('SELECT actor, method, path FROM operator_audit').fetchone()
                self.assertEqual(row, ('owner', 'POST', '/api/v1/metrics/reset'))

    def test_conflicting_batch_rolls_back_earlier_metric_and_receipt(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(api, 'DB_PATH', str(Path(directory) / 'api.db')):
            api.init_db()
            client = TestClient(api.app)
            original = dict(event(), record_id='existing')
            body = dict(batch_size=1, events=[original], exported_at=time.time())
            self.assertEqual(client.post('/api/v1/telemetry/events', json=body).status_code, 200)
            body['events'] = [dict(event(), record_id='new'), dict(original, direction='out')]
            body['batch_size'] = 2
            self.assertEqual(client.post('/api/v1/telemetry/events', json=body).status_code, 409)
            with sqlite3.connect(api.DB_PATH) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM telemetry_events').fetchone()[0], 1)
                self.assertEqual(conn.execute('SELECT count(*) FROM telemetry_receipts').fetchone()[0], 1)

class OperationalSignalsTests(unittest.TestCase):
    def test_backlog_reader_is_read_only_and_reports_pending_records(self):
        from server.runtime_readiness import read_outbox_backlog
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'outbox.db')
            self.assertIsNone(read_outbox_backlog(path))
            self.assertFalse(Path(path).exists())
            buffer = LocalBuffer(path)
            buffer.save_event(event())
            self.assertEqual(read_outbox_backlog(path)['pending_records'], 1)

    def test_device_registration_uses_device_credentials(self):
        from src.main import EdgePipeline
        pipeline = EdgePipeline.__new__(EdgePipeline)
        pipeline.device_id, pipeline.camera_contexts = 'edge-1', {}
        pipeline.detector = Mock(device='cpu')
        env = {'TELEMETRY_CLOUD_ENDPOINT': 'http://receiver/api/v1/telemetry', 'EDGESIGHT_API_KEY': 'registration-key'}
        with patch.dict(os.environ, env), patch('urllib.request.urlopen') as send:
            pipeline._register_device()
        self.assertEqual(send.call_args.args[0].get_header('X-api-key'), 'registration-key')
