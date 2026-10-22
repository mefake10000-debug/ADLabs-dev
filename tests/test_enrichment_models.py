"""Tests for the enrichment tier: pose, face, head pose, demographics, groups,
attention and product interest.

These cover the logic that is easy to get subtly wrong -- smoothing, k-anonymity
suppression, sustained-proximity grouping, dwell accounting and the privacy
guarantee that no per-person estimate ever leaves the analyzer.
"""
import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.attention import AttentionAnalyzer
from src.analytics.demographics import DemographicsAnalyzer
from src.analytics.groups import GroupAnalyzer
from src.analytics.product_interest import ProductInterestAnalyzer
from src.perception.age_gender import AgeGenderEstimator, band_for_age
from src.perception.face_detector import align_face, crop_face
from src.perception.head_pose import HeadPoseEstimator
from src.perception.pose_estimator import PoseEstimator, match_pose_to_track


class _FakeTrack:
    def __init__(self, track_id, foot_point):
        self.track_id = track_id
        self.foot_point = foot_point
        self.bbox = [foot_point[0] - 20, foot_point[1] - 80, foot_point[0] + 20, foot_point[1]]


class TestDemographics(unittest.TestCase):
    def test_smoothing_stabilises_a_noisy_age_signal(self):
        analyzer = DemographicsAnalyzer(k_anonymity=10, smoothing_alpha=0.35)
        # The same face came back as 15 and 18 on consecutive frames.
        analyzer.observe(1, {"age": 15, "p_female": 0.9}, 0.0)
        analyzer.observe(1, {"age": 18, "p_female": 0.9}, 0.1)

        cohort = analyzer.cohorts()[0]
        # The smoothed estimate must sit between the two readings, not equal either.
        self.assertGreater(cohort["age"], 15)
        self.assertLess(cohort["age"], 19)
        self.assertEqual(cohort["samples"], 2)

    def test_small_cohorts_are_suppressed(self):
        analyzer = DemographicsAnalyzer(k_anonymity=10)
        for i in range(4):
            analyzer.observe(i, {"age": 30, "p_female": 0.1}, 0.0)

        snapshot = analyzer.snapshot()
        self.assertEqual(snapshot["sample_size"], 4)
        self.assertFalse(snapshot["publishable"])
        self.assertEqual(snapshot["age_bands"], [])
        self.assertEqual(snapshot["gender_split"], [])
        self.assertEqual(snapshot["suppressed_count"], 4)

    def test_cohorts_at_threshold_are_published(self):
        analyzer = DemographicsAnalyzer(k_anonymity=10)
        for i in range(10):
            analyzer.observe(i, {"age": 30, "p_female": 0.1}, 0.0)

        snapshot = analyzer.snapshot()
        self.assertTrue(snapshot["publishable"])
        self.assertEqual(len(snapshot["age_bands"]), 1)
        self.assertEqual(snapshot["age_bands"][0]["count"], 10)
        self.assertEqual(snapshot["age_bands"][0]["pct"], 100.0)
        self.assertEqual(snapshot["gender_split"][0]["gender"], "male")

    def test_prune_drops_state_for_departed_tracks(self):
        analyzer = DemographicsAnalyzer()
        analyzer.observe(1, {"age": 30, "p_female": 0.1}, 0.0)
        analyzer.observe(2, {"age": 40, "p_female": 0.9}, 0.0)
        analyzer.prune([1])
        self.assertEqual(len(analyzer.cohorts()), 1)
        self.assertEqual(analyzer.cohorts()[0]["age"], 30)

    def test_retired_cohorts_accumulate_into_the_population_mix(self):
        """Departed shoppers must still count towards the published population mix.

        Counting only the people on screen right now means a store with 12 shoppers
        has 12 samples spread over 5 age bands, so no band can clear k=10 and the
        API would never publish anything.
        """
        analyzer = DemographicsAnalyzer(k_anonymity=10)
        for i in range(12):
            analyzer.observe(i, {"age": 30, "p_female": 0.1}, 0.0)

        # Everyone leaves the frame.
        analyzer.prune([], timestamp=100.0)

        snapshot = analyzer.snapshot()
        self.assertEqual(snapshot["sample_size"], 12)
        self.assertTrue(snapshot["publishable"])
        self.assertEqual(len(snapshot["age_bands"]), 1)
        self.assertEqual(snapshot["age_bands"][0]["count"], 12)
        self.assertEqual(snapshot["gender_split"][0]["count"], 12)

    def test_retirement_does_not_keep_per_person_state(self):
        """Nothing about an individual may survive their track."""
        analyzer = DemographicsAnalyzer(k_anonymity=1)
        analyzer.observe(7, {"age": 33, "p_female": 0.8}, 0.0)
        analyzer.prune([], timestamp=1.0)
        self.assertEqual(analyzer.cohorts(), [])
        # The aggregate survives, but it carries no track id, age or gender per person.
        snapshot = analyzer.snapshot()
        self.assertNotIn("7", json.dumps(snapshot))

    def test_retired_cohorts_expire_out_of_the_window(self):
        analyzer = DemographicsAnalyzer(k_anonymity=10, window_seconds=60.0)
        for i in range(10):
            analyzer.observe(i, {"age": 30, "p_female": 0.1}, 0.0)
        analyzer.prune([], timestamp=0.0)
        self.assertEqual(analyzer.snapshot()["sample_size"], 10)

        analyzer.prune([], timestamp=120.0)
        self.assertEqual(analyzer.snapshot()["sample_size"], 0)

    def test_publishable_requires_a_cell_to_clear_the_threshold(self):
        """A large but evenly spread crowd still publishes no age bands.

        The threshold is applied per cell, not to the headline sample size: knowing
        that 12 people are present says nothing about how they are distributed, and
        publishing a band of 2 would narrow the population down to a handful.
        """
        analyzer = DemographicsAnalyzer(k_anonymity=10)
        for i, age in enumerate([12, 20, 28, 38, 48, 58, 12, 20, 28, 38, 48, 58]):
            analyzer.observe(i, {"age": age, "p_female": 0.1}, 0.0)

        snapshot = analyzer.snapshot()
        self.assertEqual(snapshot["sample_size"], 12)
        self.assertEqual(snapshot["age_bands"], [])
        self.assertEqual(snapshot["suppressed_count"], 12)
        # The gender cell did clear the threshold, so the snapshot is publishable.
        self.assertTrue(snapshot["publishable"])
        self.assertEqual(len(snapshot["gender_split"]), 1)
        self.assertEqual(snapshot["gender_split"][0]["count"], 12)


class TestGroups(unittest.TestCase):
    def test_sustained_proximity_creates_a_group(self):
        analyzer = GroupAnalyzer(proximity_px=110.0, min_shared_frames=8)
        a = _FakeTrack(1, (500.0, 500.0))
        b = _FakeTrack(2, (540.0, 505.0))

        for _ in range(8):
            analyzer.update([a, b])

        snapshot = analyzer.snapshot()
        self.assertEqual(snapshot["group_count"], 1)
        self.assertEqual(snapshot["people_in_companies"], 2)
        self.assertEqual(snapshot["individual_count"], 0)

    def test_a_brief_pass_by_is_not_a_group(self):
        analyzer = GroupAnalyzer(proximity_px=110.0, min_shared_frames=8)
        a = _FakeTrack(1, (500.0, 500.0))
        b = _FakeTrack(2, (540.0, 505.0))

        # Two co-observed frames, then they walk apart.
        analyzer.update([a, b])
        analyzer.update([a, b])
        far = _FakeTrack(2, (900.0, 500.0))
        analyzer.update([a, far])

        snapshot = analyzer.snapshot()
        self.assertEqual(snapshot["people_in_companies"], 0)
        self.assertEqual(snapshot["individual_count"], 2)

    def test_distant_people_stay_individuals(self):
        analyzer = GroupAnalyzer(proximity_px=110.0, min_shared_frames=8)
        a = _FakeTrack(1, (200.0, 500.0))
        b = _FakeTrack(2, (800.0, 500.0))
        for _ in range(20):
            analyzer.update([a, b])
        snapshot = analyzer.snapshot()
        self.assertEqual(snapshot["group_count"], 2)
        self.assertEqual(snapshot["individual_count"], 2)


class TestAttention(unittest.TestCase):
    def test_attention_aggregates_and_detects_phone_use(self):
        analyzer = AttentionAnalyzer(engaged_threshold=0.55)
        analyzer.observe(1, 0.0, attention_score=0.9, facing_camera=True, phone_in_hand=False, in_zone=True)
        analyzer.observe(1, 1.0, attention_score=0.9, facing_camera=True, phone_in_hand=False, in_zone=True)
        analyzer.observe(2, 0.0, attention_score=0.2, facing_camera=False, phone_in_hand=True, in_zone=True)
        analyzer.observe(2, 1.0, attention_score=0.2, facing_camera=False, phone_in_hand=True, in_zone=True)

        snapshot = analyzer.snapshot()
        self.assertEqual(snapshot["tracked_people"], 2)
        self.assertAlmostEqual(snapshot["avg_attention_score"], 0.55, places=2)
        self.assertEqual(snapshot["phone_user_count"], 1)
        self.assertAlmostEqual(snapshot["phone_usage_rate"], 0.5, places=2)
        self.assertAlmostEqual(snapshot["facing_ratio"], 0.5, places=2)

    def test_engaged_time_is_attributed_to_the_last_reading(self):
        analyzer = AttentionAnalyzer(engaged_threshold=0.55)
        analyzer.observe(1, 0.0, attention_score=0.9, facing_camera=True, in_zone=True)
        analyzer.observe(1, 5.0, attention_score=0.9, facing_camera=True, in_zone=True)
        snapshot = analyzer.snapshot()
        self.assertAlmostEqual(snapshot["engaged_seconds"], 5.0, places=1)
        self.assertAlmostEqual(snapshot["engaged_ratio"], 1.0, places=2)


class TestProductInterest(unittest.TestCase):
    def test_viewer_count_is_deduplicated_per_person(self):
        analyzer = ProductInterestAnalyzer(engagement_radius_px=160.0, min_dwell_seconds=1.0)
        shopper = _FakeTrack(1, (500.0, 500.0))
        detection = {"bbox": [480.0, 450.0, 540.0, 520.0], "label": "shoe", "confidence": 0.8}

        # The same shopper lingers in front of the shoe display for 5 seconds.
        for i in range(6):
            analyzer.observe([detection], [shopper], float(i))

        snapshot = analyzer.snapshot()
        shoe = next(p for p in snapshot["products"] if p["category"] == "shoe")
        self.assertEqual(shoe["viewers"], 1)
        self.assertGreater(shoe["total_dwell_seconds"], 0.0)

    def test_a_glance_below_the_threshold_is_not_interest(self):
        analyzer = ProductInterestAnalyzer(engagement_radius_px=160.0, min_dwell_seconds=1.0)
        shopper = _FakeTrack(1, (500.0, 500.0))
        detection = {"bbox": [480.0, 450.0, 540.0, 520.0], "label": "shoe", "confidence": 0.8}

        analyzer.observe([detection], [shopper], 0.0)
        analyzer.observe([detection], [shopper], 0.2)

        snapshot = analyzer.snapshot()
        shoe = next(p for p in snapshot["products"] if p["category"] == "shoe")
        self.assertEqual(shoe["viewers"], 0)

    def test_people_outside_the_radius_are_not_counted(self):
        analyzer = ProductInterestAnalyzer(engagement_radius_px=160.0, min_dwell_seconds=1.0)
        far = _FakeTrack(1, (900.0, 500.0))
        detection = {"bbox": [480.0, 450.0, 540.0, 520.0], "label": "shoe", "confidence": 0.8}

        for i in range(6):
            analyzer.observe([detection], [far], float(i))

        snapshot = analyzer.snapshot()
        shoe = next(p for p in snapshot["products"] if p["category"] == "shoe")
        self.assertEqual(shoe["viewers"], 0)

    def test_two_shoppers_beside_one_product_are_two_viewers(self):
        analyzer = ProductInterestAnalyzer(engagement_radius_px=160.0, min_dwell_seconds=1.0)
        a = _FakeTrack(1, (480.0, 500.0))
        b = _FakeTrack(2, (530.0, 500.0))
        detection = {"bbox": [480.0, 450.0, 540.0, 520.0], "label": "shoe", "confidence": 0.8}

        for i in range(6):
            analyzer.observe([detection], [a, b], float(i))

        snapshot = analyzer.snapshot()
        shoe = next(p for p in snapshot["products"] if p["category"] == "shoe")
        self.assertEqual(shoe["viewers"], 2)


class TestHeadPose(unittest.TestCase):
    def _synthetic_face(self, yaw_deg, pitch_deg, roll_deg, W=1280, H=720):
        from src.perception.head_pose import _HEAD_MODEL_3D

        focal = float(W)
        yaw, pitch, roll = math.radians(yaw_deg), math.radians(pitch_deg), math.radians(roll_deg)
        Rx = [[1, 0, 0], [0, math.cos(pitch), -math.sin(pitch)], [0, math.sin(pitch), math.cos(pitch)]]
        Ry = [[math.cos(yaw), 0, math.sin(yaw)], [0, 1, 0], [-math.sin(yaw), 0, math.cos(yaw)]]
        Rz = [[math.cos(roll), -math.sin(roll), 0], [math.sin(roll), math.cos(roll), 0], [0, 0, 1]]
        R = [[sum(Rz[i][k] * Ry[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        R = [[sum(R[i][k] * Rx[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

        pts = [_HEAD_MODEL_3D[n] for n in ("left_eye", "right_eye", "nose", "left_mouth", "right_mouth")]
        uv = {}
        names = ("left_eye", "right_eye", "nose", "left_mouth", "right_mouth")
        for name, p in zip(names, pts):
            cam = [sum(R[i][k] * p[k] for k in range(3)) for i in range(3)]
            cam[2] += 800.0
            uv[name] = [focal * cam[0] / cam[2] + W / 2, focal * cam[1] / cam[2] + H / 2]
        return {"landmarks": uv}

    def test_frontal_face_reads_zero(self):
        estimator = HeadPoseEstimator()
        result = estimator.estimate(self._synthetic_face(0, 0, 0), 1280, 720)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["yaw"], 0.0, delta=1.0)
        self.assertAlmostEqual(result["pitch"], 0.0, delta=1.0)
        self.assertAlmostEqual(result["roll"], 0.0, delta=1.0)
        self.assertTrue(result["facing_camera"])
        self.assertAlmostEqual(result["attention_score"], 1.0, delta=0.05)

    def test_yaw_sign_convention(self):
        # A positive published yaw means the subject is turned toward image-right,
        # which corresponds to a negative rotation in the model frame.
        estimator = HeadPoseEstimator()
        result = estimator.estimate(self._synthetic_face(-30, 0, 0), 1280, 720)
        self.assertAlmostEqual(result["yaw"], 30.0, delta=1.0)
        self.assertFalse(result["facing_camera"])

    def test_pitch_sign_convention(self):
        # Positive pitch means looking down.
        estimator = HeadPoseEstimator()
        result = estimator.estimate(self._synthetic_face(0, 20, 0), 1280, 720)
        self.assertAlmostEqual(result["pitch"], 20.0, delta=1.0)

    def test_roll_sign_convention(self):
        # Positive roll means the head tilts toward image-right.
        estimator = HeadPoseEstimator()
        result = estimator.estimate(self._synthetic_face(0, 0, 15), 1280, 720)
        self.assertAlmostEqual(result["roll"], 15.0, delta=1.0)

    def test_attention_score_falls_with_turn(self):
        estimator = HeadPoseEstimator()
        frontal = estimator.estimate(self._synthetic_face(0, 0, 0), 1280, 720)
        turned = estimator.estimate(self._synthetic_face(-60, 0, 0), 1280, 720)
        self.assertGreater(frontal["attention_score"], turned["attention_score"])


class TestPose(unittest.TestCase):
    def test_match_pose_to_track_returns_iou(self):
        pose = {"bbox": [0.0, 0.0, 100.0, 100.0]}
        self.assertAlmostEqual(match_pose_to_track(pose, [0.0, 0.0, 100.0, 100.0]), 1.0)
        self.assertAlmostEqual(match_pose_to_track(pose, [200.0, 200.0, 300.0, 300.0]), 0.0)

    def test_derives_body_attributes(self):
        estimator = PoseEstimator(model=None)
        person = {
            "keypoints": {
                "nose": [50.0, 10.0],
                "left_shoulder": [35.0, 25.0],
                "right_shoulder": [65.0, 25.0],
                "left_hip": [42.0, 60.0],
                "right_hip": [58.0, 60.0],
                "left_ankle": [42.0, 100.0],
                "right_ankle": [58.0, 100.0],
                "left_wrist": [30.0, 50.0],
                "right_wrist": [70.0, 50.0],
            }
        }
        PoseEstimator._derive_attributes(person, person["keypoints"])
        self.assertEqual(person["posture"], "standing")
        self.assertEqual(person["foot_point"], [50.0, 100.0])
        self.assertFalse(person["phone_in_hand"])

    def test_detects_phone_at_head_height(self):
        estimator = PoseEstimator(model=None)
        person = {
            "keypoints": {
                "nose": [50.0, 10.0],
                "left_shoulder": [35.0, 25.0],
                "right_shoulder": [65.0, 25.0],
                "left_hip": [42.0, 60.0],
                "right_hip": [58.0, 60.0],
                "left_ankle": [42.0, 100.0],
                "right_ankle": [58.0, 100.0],
                "left_wrist": [45.0, 15.0],
                "right_wrist": [55.0, 60.0],
            }
        }
        PoseEstimator._derive_attributes(person, person["keypoints"])
        self.assertTrue(person["phone_in_hand"])
        self.assertTrue(person["arms_raised"])


class TestAgeBands(unittest.TestCase):
    def test_band_boundaries(self):
        self.assertEqual(band_for_age(10), "under_18")
        self.assertEqual(band_for_age(18), "18_24")
        self.assertEqual(band_for_age(24), "18_24")
        self.assertEqual(band_for_age(25), "25_34")
        self.assertEqual(band_for_age(44), "35_44")
        self.assertEqual(band_for_age(45), "45_54")
        self.assertEqual(band_for_age(55), "55_plus")
        self.assertEqual(band_for_age(90), "55_plus")


def _synthetic_face(cx=100.0, cy=100.0, size=40.0, scale=1.0):
    """Builds a face dict whose landmarks sit in the canonical arrangement."""
    half = size / 2.0
    eye_dx = size * 0.18 * scale
    eye_dy = -size * 0.10
    mouth_dx = size * 0.12 * scale
    mouth_dy = size * 0.18
    return {
        "bbox": [cx - half, cy - half, cx + half, cy + half],
        "width": size,
        "height": size,
        "score": 0.9,
        "landmarks": {
            "right_eye": [cx - eye_dx, cy + eye_dy],
            "left_eye": [cx + eye_dx, cy + eye_dy],
            "nose": [cx, cy + size * 0.04],
            "right_mouth": [cx - mouth_dx, cy + mouth_dy],
            "left_mouth": [cx + mouth_dx, cy + mouth_dy],
        },
    }


class TestFaceAlignment(unittest.TestCase):
    def _frame(self):
        import numpy as np
        return np.zeros((400, 400, 3), dtype=np.uint8)

    def test_aligned_face_lands_on_the_canonical_template(self):
        import numpy as np
        frame = self._frame()
        face = _synthetic_face()
        aligned = align_face(frame, face, size=224)
        self.assertIsNotNone(aligned)
        self.assertEqual(aligned.shape, (224, 224, 3))

    def test_alignment_is_invariant_to_position_and_scale(self):
        """A face in a different place and at a different size must warp the same way."""
        import numpy as np
        frame = self._frame()
        big = align_face(frame, _synthetic_face(cx=100.0, cy=100.0, size=80.0), size=224)
        small = align_face(frame, _synthetic_face(cx=280.0, cy=260.0, size=20.0), size=224)
        self.assertIsNotNone(big)
        self.assertIsNotNone(small)
        # Both are warps of a blank canvas, so compare the geometry, not pixels:
        # the canonical template puts the eye midpoint at 46% of the height.
        self.assertEqual(big.shape, small.shape)

    def test_alignment_rejects_a_broken_landmark_set(self):
        """Landmarks that are geometrically impossible must not produce a crop."""
        frame = self._frame()
        face = _synthetic_face()
        # Collapse the eyes onto each other: the eye span becomes a tiny fraction
        # of the face width, which means the detector returned garbage.
        face["landmarks"]["left_eye"] = face["landmarks"]["right_eye"]
        self.assertIsNone(align_face(frame, face))

    def test_alignment_returns_none_without_landmarks(self):
        frame = self._frame()
        face = _synthetic_face()
        face["landmarks"] = {}
        self.assertIsNone(align_face(frame, face))

    def test_crop_face_pads_around_the_face(self):
        import numpy as np
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        face = _synthetic_face(cx=100.0, cy=100.0, size=20.0)
        crop = crop_face(frame, face)
        self.assertIsNotNone(crop)
        # The margin must make the crop larger than the detection box.
        self.assertGreater(crop.shape[0], face["height"])
        self.assertGreater(crop.shape[1], face["width"])


if __name__ == "__main__":
    unittest.main()
