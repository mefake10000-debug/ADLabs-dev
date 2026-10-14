"""
M4 tracking accuracy benchmark harness.

Runs the real detection+tracking pipeline (PersonDetector -> SimpleByteTracker,
optionally -> Tripwire) against a video and compares the result against a small,
manually-verified ground-truth JSON file. Detector and tracker settings come from
configs/pipeline.yaml (the same file the edge analyzer uses), so numbers reflect
production configuration unless you explicitly override them.

Usage (inside the edge container, where YOLO actually loads):
    docker compose run --rm edge-analyzer python scripts/benchmark_tracking.py \
        data/sample_videos/entrance_sample.mp4 \
        --ground-truth scripts/benchmark_ground_truth/entrance_sample.json

Ground truth JSON (see scripts/benchmark_ground_truth/*.json):
{
  "video": "...",
  "method": "point-in-time headcount",
  "checkpoints": [{"frame_index": 150, "expected_visible_people": 14}, ...],
  "notes": "how the counts were derived"
}
(the older single-frame form with top-level frame_index / expected_visible_people
is still accepted), or
{
  "method": "tripwire crossings",
  "expected_in": 4, "expected_out": 2, "expected_unique_people": 6,
  "tripwire_line": [[400, 360], [880, 360]], "tripwire_direction": "top_to_bottom"
}

At every headcount checkpoint two numbers are reported:
  * raw detections      - what the detector found (after size/aspect filters)
  * tracker output      - what the tracker hands to analytics/dashboard, i.e. after
                          min_hits confirmation and stationary suppression
The gap between them is the cost of the tracker's filtering.

This script refuses to run when YOLO cannot load (there is no fallback detector), so it
only works where torch/ultralytics do: the edge container.
"""
import argparse
import json
import os
import sys
import time

import cv2
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.detector import PersonDetector
from src.perception.tracker import SimpleByteTracker
from src.analytics.tripwire import Tripwire

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "..", "configs", "pipeline.yaml")


def load_pipeline_config(path: str) -> dict:
    if path and os.path.exists(path):
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def build_detector(cfg: dict, conf_thresh=None, model=None) -> PersonDetector:
    p = cfg.get("perception", {})
    return PersonDetector(
        model_name=model or p.get("model_name", "yolov8n.pt"),
        conf_thresh=conf_thresh if conf_thresh is not None else p.get("confidence_threshold", 0.50),
        iou_thresh=p.get("iou_threshold", 0.45),
        min_height=p.get("min_height", 85.0),
        min_width=p.get("min_width", 30.0),
        min_aspect_ratio=p.get("min_aspect_ratio", 1.0),
        max_aspect_ratio=p.get("max_aspect_ratio", 4.2),
        min_area=p.get("min_area", 3000.0),
    )


def build_tracker(cfg: dict) -> SimpleByteTracker:
    t = cfg.get("tracking", {})
    return SimpleByteTracker(
        max_age=t.get("track_buffer", 30),
        iou_threshold=t.get("match_thresh", 0.45),
        min_hits=t.get("min_hits", 4),
        stationary_policy=t.get("stationary_policy", "tag"),
        track_thresh=t.get("track_thresh", 0.5),
    )


def stage_breakdown(detector: PersonDetector, frame, conf_thresh: float, low_conf: float = 0.25):
    """Where do people get lost *before* the tracker? Runs the raw YOLO model on one frame and
    counts person boxes at each stage: at low confidence, at the configured confidence, and how many
    of those the size / aspect filters then reject. Returns None when YOLO isn't loaded."""
    if detector.model is None:
        return None

    def person_boxes(conf):
        results = detector.model.predict(source=frame, classes=[0], conf=conf, iou=detector.iou_thresh,
                                         device=detector.device, verbose=False)
        boxes = []
        if results:
            for b in results[0].boxes:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                boxes.append((x2 - x1, y2 - y1))
        return boxes

    at_conf = person_boxes(conf_thresh)
    too_small = aspect_rejected = 0
    for w, h in at_conf:
        if h < detector.min_height or w < detector.min_width or w * h < detector.min_area:
            too_small += 1
        elif not (detector.min_aspect_ratio <= h / max(1.0, w) <= detector.max_aspect_ratio):
            aspect_rejected += 1
    return {
        "yolo_low_conf": len(person_boxes(low_conf)),
        "yolo_at_conf": len(at_conf),
        "rejected_size": too_small,
        "rejected_aspect": aspect_rejected,
    }


def checkpoints_from(ground_truth: dict) -> dict:
    """{frame_index: expected_people}"""
    if not ground_truth or ground_truth.get("method") != "point-in-time headcount":
        return {}
    if "checkpoints" in ground_truth:
        return {c["frame_index"]: c["expected_visible_people"] for c in ground_truth["checkpoints"]}
    return {ground_truth["frame_index"]: ground_truth["expected_visible_people"]}


def run_benchmark(video_path: str, ground_truth: dict = None, max_frames: int = 100000,
                  conf_thresh=None, config_path: str = DEFAULT_CONFIG, model=None):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: could not open {video_path}")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    cfg = load_pipeline_config(config_path)
    detector = build_detector(cfg, conf_thresh, model)
    if detector.model is None:
        print("ERROR: YOLO did not load, so any accuracy number would be meaningless. "
              "Run this inside the edge container (docker compose run --rm --no-deps edge-analyzer ...).")
        return None
    backend = f"YOLO ({detector.model_name})"
    tracker = build_tracker(cfg)

    tripwire = None
    if ground_truth and ground_truth.get("method") == "tripwire crossings":
        tripwire = Tripwire(
            wire_id="benchmark_tw",
            name="Benchmark Tripwire",
            line=ground_truth["tripwire_line"],
            in_direction=ground_truth.get("tripwire_direction", "top_to_bottom"),
        )

    checkpoints = checkpoints_from(ground_truth)
    last_needed = max(checkpoints) if checkpoints else max_frames
    limit = min(max_frames, total_frames, last_needed + 1)

    frame_idx = 0
    unique_track_ids = set()
    observed = {}   # frame_index -> (raw detections, tracker output)
    stages = {}     # frame_index -> stage_breakdown(...)
    effective_conf = conf_thresh if conf_thresh is not None else cfg.get("perception", {}).get("confidence_threshold", 0.5)
    t0 = time.time()

    while frame_idx < limit:
        ret, frame = cap.read()
        if not ret:
            break
        current_time = t0 + (frame_idx / fps)

        dets = detector.detect(frame)
        tracks = tracker.update(dets, current_time)
        unique_track_ids.update(t.track_id for t in tracks)

        if tripwire is not None:
            tripwire.update(tracks, current_time)
        if frame_idx in checkpoints:
            observed[frame_idx] = (len(dets), len(tracks))
            breakdown = stage_breakdown(detector, frame, effective_conf)
            if breakdown:
                stages[frame_idx] = breakdown

        frame_idx += 1

    cap.release()

    result = {
        "video": video_path,
        "backend": backend,
        "config": os.path.relpath(config_path) if config_path and os.path.exists(config_path) else "built-in defaults",
        "resolution": f"{width}x{height}",
        "frames_processed": frame_idx,
        "duration_s": round(frame_idx / fps, 1),
        "wall_clock_s": round(time.time() - t0, 1),
        "unique_track_ids": len(unique_track_ids),
    }

    if tripwire is not None:
        counts = tripwire.get_counts()
        result["predicted_in"] = counts["in_count"]
        result["predicted_out"] = counts["out_count"]

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

        rows = []
        for frame in sorted(observed):
            expected = checkpoints[frame]
            raw, out = observed[frame]
            rows.append({
                "frame_index": frame, "expected": expected, "raw_detections": raw, "tracker_output": out,
                **({"stages": stages[frame]} if frame in stages else {}),
                "raw_recall": round(raw / expected, 3) if expected else None,
                "tracker_recall": round(out / expected, 3) if expected else None,
            })
        if rows:
            result["checkpoints"] = rows
            result["mean_raw_recall"] = round(sum(r["raw_recall"] for r in rows) / len(rows), 3)
            result["mean_tracker_recall"] = round(sum(r["tracker_recall"] for r in rows) / len(rows), 3)

    return result


def print_result(result: dict):
    print("=" * 74)
    print(f"Video:              {result['video']}")
    print(f"Detector backend:   {result['backend']}")
    print(f"Pipeline config:    {result['config']}")
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
            print(f"ID fragmentation estimate (extra IDs beyond known unique people): {result['id_fragmentation_estimate']}")

    if "checkpoints" in result:
        print("\n  frame | hand count | raw detections | tracker output | raw recall | tracker recall")
        for r in result["checkpoints"]:
            print(f"  {r['frame_index']:5d} | {r['expected']:10d} | {r['raw_detections']:14d} | {r['tracker_output']:14d} | "
                  f"{r['raw_recall'] * 100:9.0f}% | {r['tracker_recall'] * 100:13.0f}%")
        if any("stages" in r for r in result["checkpoints"]):
            print("\n  where people are lost before the tracker (YOLO person boxes):")
            print("  frame | hand count | yolo conf>=0.25 | yolo at config conf | size-rejected | aspect-rejected | kept")
            for r in result["checkpoints"]:
                st = r.get("stages")
                if st:
                    print(f"  {r['frame_index']:5d} | {r['expected']:10d} | {st['yolo_low_conf']:15d} | {st['yolo_at_conf']:19d} | "
                          f"{st['rejected_size']:13d} | {st['rejected_aspect']:15d} | {r['raw_detections']:4d}")
        print(f"\n  mean raw-detection recall: {result['mean_raw_recall'] * 100:.0f}%   "
              f"mean tracker-output recall: {result['mean_tracker_recall'] * 100:.0f}%")

    if result.get("ground_truth_notes"):
        print(f"\nGround truth notes: {result['ground_truth_notes']}")
    print("=" * 74)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="M4 tracking accuracy benchmark")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--ground-truth", help="Path to ground truth JSON", default=None)
    parser.add_argument("--config", help="Pipeline config (default: configs/pipeline.yaml)", default=DEFAULT_CONFIG)
    parser.add_argument("--max-frames", type=int, default=100000)
    parser.add_argument("--conf-thresh", type=float, default=None, help="Override perception.confidence_threshold")
    parser.add_argument("--model", default=None,
                        help="Override perception.model_name, e.g. models/yolo26n.pt (downloaded on first use)")
    args = parser.parse_args()

    # Windows shells hand over backslash paths; inside the Linux container they aren't separators
    args.video = args.video.replace("\\", "/")
    if args.ground_truth:
        args.ground_truth = args.ground_truth.replace("\\", "/")
    args.config = args.config.replace("\\", "/")

    gt = None
    if args.ground_truth:
        with open(args.ground_truth, "r") as f:
            gt = json.load(f)

    result = run_benchmark(args.video, ground_truth=gt, max_frames=args.max_frames,
                           conf_thresh=args.conf_thresh, config_path=args.config, model=args.model)
    if result is None:
        sys.exit(2)
    print_result(result)
