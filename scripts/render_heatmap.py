"""
Whole-clip floor heatmap for a video: where people spent time, over the entire clip.

Uses the same Heatmap as the live edge analyzer (src/analytics/heatmap.py). Tracks come from a
previous detect_id_switches.py run's tracks.jsonl (seconds, no YOLO), or from running the real
detector + tracker when --tracks is omitted (edge container only). Staff aren't tagged here --
staff zones are a live-pipeline feature -- so cashiers show up as hot spots behind the counter.

    docker compose run --rm --no-deps edge-analyzer python scripts/render_heatmap.py \
        data/sample_videos/entrance_sample.mp4 \
        --tracks data/storage/id_switch_runs/<run>/tracks.jsonl

Writes data/storage/heatmaps/<video>_clip.jpg (gitignored) and prints the hottest spots. The
background is the median of frames sampled across the clip, which removes passers-by and leaves
an empty shop floor, so the colours aren't drawn over whoever happened to be in one frame.
"""
import argparse
import os
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmark_tracking import DEFAULT_CONFIG, build_detector, build_tracker, load_pipeline_config  # noqa: E402
from detect_id_switches import live_tracks, replayed_tracks  # noqa: E402
from src.analytics.heatmap import Heatmap  # noqa: E402

BACKGROUND_SAMPLES = 25


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video")
    parser.add_argument("--tracks", default=None, help="tracks.jsonl from a detect_id_switches.py run (no YOLO)")
    parser.add_argument("--process-fps", type=float, default=None, help="Only without --tracks")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        sys.exit(f"ERROR: could not open {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    sample_every = max(1, total // BACKGROUND_SAMPLES)

    stem = os.path.splitext(os.path.basename(args.video))[0]
    out = args.out or os.path.join(ROOT, "data", "storage", "heatmaps", f"{stem}_clip.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if args.tracks:
        frames = replayed_tracks(cap, args.tracks)
    else:
        cfg = load_pipeline_config(DEFAULT_CONFIG)
        detector = build_detector(cfg)
        if detector.model is None:
            sys.exit("ERROR: YOLO did not load. Pass --tracks, or run inside the edge container.")
        frames = live_tracks(cap, fps, args.process_fps, detector, build_tracker(cfg), open(os.devnull, "w"))

    heatmap, samples = None, []
    for frame_idx, t, frame, tracks in frames:
        if heatmap is None:
            heatmap = Heatmap(frame.shape[1], frame.shape[0])
        heatmap.add(tracks, t)
        if frame_idx // sample_every > len(samples) - 1 and len(samples) < BACKGROUND_SAMPLES:
            samples.append(frame)
    cap.release()
    if heatmap is None:
        sys.exit("ERROR: no frames processed")

    background = np.median(np.stack(samples), axis=0).astype(np.uint8)
    cv2.imwrite(out, heatmap.render(background))

    smooth = cv2.GaussianBlur(heatmap.grid, (0, 0), sigmaX=1.2)
    print(f"Heatmap written to {out}")
    print(f"{heatmap.total_person_seconds / 60:.1f} person-minutes over "
          f"{(heatmap.last_time - heatmap.started_at) / 60:.1f} min of footage")
    print("Hottest spots (pixel centre of a cell, person-seconds there):")
    for flat in np.argsort(smooth, axis=None)[::-1][:5]:
        row, col = np.unravel_index(flat, smooth.shape)
        print(f"  x={col * heatmap.cell + heatmap.cell // 2:4d}, y={row * heatmap.cell + heatmap.cell // 2:4d}: "
              f"{heatmap.grid[row, col]:.1f}s")


if __name__ == "__main__":
    main()
