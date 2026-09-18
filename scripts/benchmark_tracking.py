"""
M4 tracking accuracy benchmark harness.

Runs the real detection+tracking pipeline (PersonDetector -> SimpleByteTracker,
optionally -> Tripwire) against a video and compares the result against a small,
manually-verified ground-truth JSON file. Produces a documented count-accuracy
and ID-stability number instead of shipping tracker changes on "looks right".

Usage:
    python scripts/benchmark_tracking.py <video_path> [--ground-truth <json_path>]
                                          [--max-frames N] [--conf-thresh F]

Ground truth JSON schema (see scripts/benchmark_ground_truth/*.json):
{
  "video": "data/sample_videos/mall_entrance_topdown_01.mp4",
  "method": "point-in-time headcount" | "tripwire crossings",
  "notes": "free text describing exactly how the ground truth was derived",
  "frame_index": 500,                  # required for point-in-time headcount
  "expected_visible_people": 9,         # required for point-in-time headcount
  "expected_in": 4,                     # required for tripwire crossings
  "expected_out": 2,                    # required for tripwire crossings
  "tripwire_line": [[400, 360], [880, 360]],
  "tripwire_direction": "top_to_bottom"
}

IMPORTANT CAVEAT: this harness uses whatever detector PersonDetector resolves
to. If ultralytics/torch cannot load (see PersonDetector._init_model), it
silently runs on the classical HOG+SVM fallback detector instead of YOLO,
which is meaningfully less accurate on small/distant/angled figures. Every
result this script prints states which detector backend actually ran, and
report authors MUST carry that caveat into any written summary.
"""
import argparse
import json
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.detector import PersonDetector
from src.perception.tracker import SimpleByteTracker
from src.analytics.tripwire import Tripwire


def run_benchmark(video_path: str, ground_truth: dict = None, max_frames: int = 100000, conf_thresh: float = 0.35):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: could not open {video_path}")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    detector = PersonDetector(conf_thresh=conf_thresh, min_height=40.0, min_width=15.0, min_area=600.0)
    backend = "YOLO (ultralytics)" if detector.model is not None else "HOG+SVM fallback (classical CV)"

    tracker = SimpleByteTracker(max_age=30, iou_threshold=0.3, min_hits=2)

    tripwire = None
    if ground_truth and ground_truth.get("method") == "tripwire crossings":
        tripwire = Tripwire(
            wire_id="benchmark_tw",
            name="Benchmark Tripwire",
            line=ground_truth["tripwire_line"],
            in_direction=ground_truth.get("tripwire_direction", "top_to_bottom")
        )

    frame_idx = 0
    unique_track_ids = set()
    detections_at_target_frame = None
    t0 = time.time()

    while frame_idx < min(max_frames, total_frames):
        ret, frame = cap.read()
        if not ret:
            break
        current_time = t0 + (frame_idx / fps)

        dets = detector.detect(frame)
        tracks = tracker.update(dets, current_time)
        unique_track_ids.update(t.track_id for t in tracks)

        if tripwire is not None:
            tripwire.update(tracks, current_time)

        if ground_truth and ground_truth.get("method") == "point-in-time headcount" \
                and frame_idx == ground_truth.get("frame_index"):
            detections_at_target_frame = len(dets)

        frame_idx += 1

    cap.release()
    elapsed = time.time() - t0

    result = {
        "video": video_path,
        "backend": backend,
        "resolution": f"{width}x{height}",
        "frames_processed": frame_idx,
        "duration_s": round(frame_idx / fps, 1),
        "wall_clock_s": round(elapsed, 1),
        "unique_track_ids": len(unique_track_ids),
    }

    if tripwire is not None:
        counts = tripwire.get_counts()
        result["predicted_in"] = counts["in_count"]
        result["predicted_out"] = counts["out_count"]

    if detections_at_target_frame is not None:
        result["detections_at_target_frame"] = detections_at_target_frame
        result["target_frame_index"] = ground_truth["frame_index"]

    if ground_truth:
        result["ground_truth_method"] = ground_truth.get("method")
        result["ground_truth_notes"] = ground_truth.get("notes")

        if ground_truth.get("method") == "tripwire crossings":
            expected_in = ground_truth.get("expected_in", 0)
            expected_out = ground_truth.get("expected_out", 0)
            result["expected_in"] = expected_in
            result["expected_out"] = expected_out
            expected_total = expected_in + expected_out
            predicted_total = result.get("predicted_in", 0) + result.get("predicted_out", 0)
            if expected_total > 0:
                result["count_accuracy"] = round(1.0 - abs(predicted_total - expected_total) / expected_total, 3)
            expected_unique = ground_truth.get("expected_unique_people")
            if expected_unique:
                result["expected_unique_people"] = expected_unique
                result["id_fragmentation_estimate"] = max(0, len(unique_track_ids) - expected_unique)

        elif ground_truth.get("method") == "point-in-time headcount":
            expected = ground_truth.get("expected_visible_people", 0)
            result["expected_visible_people"] = expected
            if expected > 0 and detections_at_target_frame is not None:
                result["detection_recall_at_frame"] = round(detections_at_target_frame / expected, 3)

    return result


def print_result(result: dict):
    print("=" * 70)
    print(f"Video:              {result['video']}")
    print(f"Detector backend:   {result['backend']}")
    print(f"Resolution:         {result['resolution']}")
    print(f"Frames processed:   {result['frames_processed']} ({result['duration_s']}s of footage)")
    print(f"Wall-clock time:    {result['wall_clock_s']}s")
    print(f"Unique track IDs:   {result['unique_track_ids']}")

    if "predicted_in" in result:
        print(f"Predicted IN/OUT:   {result['predicted_in']} / {result['predicted_out']}")
        print(f"Expected IN/OUT:    {result.get('expected_in')} / {result.get('expected_out')}")
        if "count_accuracy" in result:
            print(f"Count accuracy:     {result['count_accuracy'] * 100:.1f}%")
        if "id_fragmentation_estimate" in result:
            print(f"ID fragmentation estimate (extra track IDs beyond known unique people): {result['id_fragmentation_estimate']}")

    if "detections_at_target_frame" in result:
        print(f"Detections @ frame {result['target_frame_index']}: {result['detections_at_target_frame']} (expected ~{result.get('expected_visible_people')})")
        if "detection_recall_at_frame" in result:
            print(f"Detection recall @ frame: {result['detection_recall_at_frame'] * 100:.1f}%")

    if result.get("ground_truth_notes"):
        print(f"Ground truth notes: {result['ground_truth_notes']}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="M4 tracking accuracy benchmark")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--ground-truth", help="Path to ground truth JSON", default=None)
    parser.add_argument("--max-frames", type=int, default=100000)
    parser.add_argument("--conf-thresh", type=float, default=0.35)
    args = parser.parse_args()

    gt = None
    if args.ground_truth:
        with open(args.ground_truth, "r") as f:
            gt = json.load(f)

    result = run_benchmark(args.video, ground_truth=gt, max_frames=args.max_frames, conf_thresh=args.conf_thresh)
    if result:
        print_result(result)
