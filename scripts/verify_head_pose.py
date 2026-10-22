"""Empirical checks on the head-pose convention and YuNet landmark naming.

Run: python scripts/verify_head_pose.py
"""
import os
import sys
import glob

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.face_detector import FaceDetector
from src.perception.head_pose import HeadPoseEstimator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
YU = os.path.join(ROOT, "models/onnx/face_detection_yunet_2023mar.onnx")


def check_landmark_naming():
    """YuNet's 'right_eye' -- is it the subject's anatomical right (image-left for a
    frontal face) or the image-right eye? The whole head model depends on this."""
    videos = sorted(glob.glob(os.path.join(ROOT, "data/sample_videos/*.mp4")))
    if not videos:
        print("no sample video; skipping landmark naming check")
        return
    det = FaceDetector(YU, score_threshold=0.5)
    est = HeadPoseEstimator()
    readings = []
    for vid in videos[:2]:
        cap = cv2.VideoCapture(vid)
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            idx += 1
            if idx % 15:
                continue
            faces = det.detect(frame)
            for f in faces:
                lm = f["landmarks"]
                dx = lm["left_eye"][0] - lm["right_eye"][0]
                readings.append((dx, f["width"], f["height"], est.estimate(f, frame.shape[1], frame.shape[0])))
            if len(readings) > 60:
                break
        cap.release()
        if len(readings) > 60:
            break

    if not readings:
        print("no faces found; skipping landmark naming check")
        return

    frontal = [r for r in readings if r[1] >= 24 and abs(r[3]["yaw"]) < 25 and abs(r[3]["pitch"]) < 25]
    print(f"faces sampled: {len(readings)}, frontal-ish: {len(frontal)}")
    if frontal:
        dx = np.mean([r[0] for r in frontal])
        print(f"mean x(left_eye) - x(right_eye) on frontal faces: {dx:+.1f} px")
        if dx > 0:
            print("=> left_eye is image-RIGHT of right_eye: YuNet naming is ANATOMICAL")
        else:
            print("=> left_eye is image-LEFT of right_eye: YuNet naming is IMAGE-ORDER")
    for r in readings[:8]:
        p = r[3]
        print(f"  face {r[1]:.0f}x{r[2]:.0f} dx={r[0]:+.1f} yaw={p['yaw']:+.1f} pitch={p['pitch']:+.1f} roll={p['roll']:+.1f}")


def check_synthetic():
    """Projects the 3D head model with a known rotation and checks the recovered
    angles. This is the ground truth for the axis naming."""
    from src.perception.head_pose import _HEAD_MODEL_3D

    est = HeadPoseEstimator()
    W, H = 1280, 720
    focal = W

    def project(angles_deg):
        yaw, pitch, roll = [np.deg2rad(a) for a in angles_deg]
        # Model frame: +X image-right (subject's left), +Y down, +Z into the head.
        Rx = np.array([[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]])
        Ry = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
        Rz = np.array([[np.cos(roll), -np.sin(roll), 0], [np.sin(roll), np.cos(roll), 0], [0, 0, 1]])
        R = Rz @ Ry @ Rx
        pts = np.array([_HEAD_MODEL_3D[n] for n in ("left_eye", "right_eye", "nose", "left_mouth", "right_mouth")])
        # Camera sits 800mm in front of the nose tip (OpenCV: +Z points into the scene).
        cam = pts @ R.T + np.array([0.0, 0.0, 800.0])
        u = focal * cam[:, 0] / cam[:, 2] + W / 2
        v = focal * cam[:, 1] / cam[:, 2] + H / 2
        return u, v, R

    u, v, R = project((0, 0, 0))
    lm = {
        "left_eye": [u[0], v[0]], "right_eye": [u[1], v[1]], "nose": [u[2], v[2]],
        "left_mouth": [u[3], v[3]], "right_mouth": [u[4], v[4]],
    }
    res = est.estimate({"landmarks": lm}, W, H)
    print(f"frontal -> yaw={res['yaw']:+.1f} pitch={res['pitch']:+.1f} roll={res['roll']:+.1f}")

    # Camera-frame check: with the model as defined, "turned toward image-right"
    # means the face's outward normal (model -Z) rotates toward +X.
    # Rotation signs are derived from the model frame (X right, Y down, Z into head):
    # a positive Y rotation swings the face's outward normal toward image-LEFT.
    for label, angles in [
        ("turned image-LEFT 25", (25, 0, 0)),
        ("turned image-RIGHT 25", (-25, 0, 0)),
        ("looking DOWN 20", (0, 20, 0)),
        ("looking UP 20", (0, -20, 0)),
        ("tilt RIGHT 15", (0, 0, 15)),
        ("tilt LEFT 15", (0, 0, -15)),
    ]:
        u, v, _ = project(angles)
        lm = {
            "left_eye": [u[0], v[0]], "right_eye": [u[1], v[1]], "nose": [u[2], v[2]],
            "left_mouth": [u[3], v[3]], "right_mouth": [u[4], v[4]],
        }
        res = est.estimate({"landmarks": lm}, W, H)
        print(f"  {label:24s} -> yaw={res['yaw']:+7.1f} pitch={res['pitch']:+7.1f} roll={res['roll']:+7.1f}")


if __name__ == "__main__":
    check_synthetic()
    print()
    check_landmark_naming()
