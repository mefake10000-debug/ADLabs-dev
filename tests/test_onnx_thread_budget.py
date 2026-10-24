"""Real-session checks: enrichment models must leave CPU for detection."""
import os
import unittest
from src.perception.rtmpose_estimator import RTMPoseFootEstimator
from src.perception.reid import SoftReIdExtractor

class ThreadBudgetTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MODEL_PACK_ROOT'), 'requires installed model pack')
    def test_pose_session_uses_one_worker(self):
        pose = RTMPoseFootEstimator.__new__(RTMPoseFootEstimator)
        pose._pose = None
        pose._session = None
        pose._try_ort(__import__('pathlib').Path(os.environ['MODEL_PACK_ROOT']) / '07-pose/rtmpose-t.onnx')
        self.assertTrue(pose.active)
        self.assertEqual(pose._session.get_session_options().intra_op_num_threads, 1)

    @unittest.skipUnless(os.environ.get('MODEL_PACK_ROOT'), 'requires installed model pack')
    def test_reid_session_uses_one_worker(self):
        path = os.path.join(os.environ['MODEL_PACK_ROOT'], '03-reid/osnet_x0_25_msmt17.onnx')
        model = SoftReIdExtractor(enabled=True, weights=path, onnx_weights=path)
        self.assertTrue(model.active)
        self.assertEqual(model._session.get_session_options().intra_op_num_threads, 1)

    @unittest.skipUnless(os.environ.get('MODEL_PACK_ROOT'), 'requires installed model pack')
    def test_rtmlib_session_uses_one_worker(self):
        pose=RTMPoseFootEstimator(onnx_path=os.path.join(os.environ['MODEL_PACK_ROOT'], '07-pose/rtmpose-t.onnx'))
        session=pose._pose.session if pose._pose is not None else pose._session
        self.assertEqual(session.get_session_options().intra_op_num_threads,1)
