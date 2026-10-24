"""
Make a hand-count sheet for a clip, to check "do the people the tracker sees match what a person
sees?" with a real number instead of an impression.

Picks N evenly spaced frames (skipping grey/damaged ones), saves each as a full-size image with
its checkpoint number, plus an overview sheet, and writes a ground-truth template with an empty
count per checkpoint. You count the people in each image and fill the numbers in; then
scripts/benchmark/benchmark_tracking.py scores the tracker against them (see docs/tools/footage-tools.md).

    docker compose run --rm --no-deps edge-analyzer python scripts/benchmark/make_count_sheet.py \\
        data/sample_videos/garage/garage_part00.mp4 --checkpoints 10

Output (gitignored): data/storage/count_checks/<clip>/
  checkpoint_NN_fFRAME.jpg   one per checkpoint -- count from these
  sheet.jpg                  all checkpoints at a glance
  ground_truth.json          fill in "expected_visible_people" for each checkpoint
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

COUNTING_RULE = (
    "Count every person whose head or upper body is clearly visible, including staff, people partly "
    "cut off by the frame edge or hidden behind objects, and small children. Ignore fragments too small "
    "or hidden to call (e.g. only a hand or a pair of feet). Same rule as entrance_sample.json, so "
    "numbers are comparable across clips."
)


def looks_damaged(img):
    """Grey decoder fill or large black wedges from a corrupted frame."""
    g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (160, 90))
    return np.mean(np.abs(g.astype(np.int16) - 128) <= 3) > 0.4 or np.mean(g <= 8) > 0.15


def mmss(seconds):
    return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--checkpoints", type=int, default=10)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--skip-start", type=float, default=10.0,
                    help="Seconds to skip at the start (the tracker needs a moment to confirm people)")
    args = ap.parse_args()
    video = args.video.replace("\\", "/")

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        sys.exit(f"ERROR: could not open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    stem = os.path.splitext(os.path.basename(video))[0]
    out_dir = args.out_dir or os.path.join(ROOT, "data", "storage", "count_checks", stem)
    os.makedirs(out_dir, exist_ok=True)

    first = min(total - 1, int(args.skip_start * fps))
    span = total - 1 - first
    targets = [first + int(span * (i + 0.5) / args.checkpoints) for i in range(args.checkpoints)]

    checkpoints, tiles = [], []
    for n, target in enumerate(targets, start=1):
        # Nudge forward (up to ~10 s) past damaged frames: a grey frame has no people to count.
        frame_idx, img = None, None
        for attempt in range(0, int(10 * fps), max(1, int(fps))):
            idx = min(total - 1, target + attempt)
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, candidate = cap.read()
            if ok and not looks_damaged(candidate):
                frame_idx, img = idx, candidate
                break
        if img is None:
            print(f"  checkpoint {n}: only damaged frames near {mmss(target / fps)}, skipped")
            continue

        name = f"checkpoint_{n:02d}_f{frame_idx:06d}.jpg"
        labelled = cv2.copyMakeBorder(img, 40, 0, 0, 0, cv2.BORDER_CONSTANT, value=(20, 20, 20))
        cv2.putText(labelled, f"Checkpoint {n}  |  frame {frame_idx}  |  {mmss(frame_idx / fps)}  |  count the people",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(out_dir, name), labelled)
        tiles.append(cv2.resize(labelled, (480, int(480 * labelled.shape[0] / labelled.shape[1]))))
        checkpoints.append({"checkpoint": n, "frame_index": frame_idx, "video_time": mmss(frame_idx / fps),
                            "image": name, "expected_visible_people": None})
    cap.release()

    if tiles:
        while len(tiles) % 4:
            tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(os.path.join(out_dir, "sheet.jpg"),
                    np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]))

    template = {
        "video": video,
        "method": "point-in-time headcount",
        "counting_rule": COUNTING_RULE,
        "checkpoints": checkpoints,
        "notes": "Counted by <name>, <date>. Mention anything ambiguous (e.g. a reflection, a person mostly hidden).",
    }
    gt_path = os.path.join(out_dir, "ground_truth.json")
    if os.path.exists(gt_path):
        gt_path = os.path.join(out_dir, "ground_truth.new.json")  # never overwrite counts already entered
    with open(gt_path, "w") as f:
        json.dump(template, f, indent=2)

    print(f"{len(checkpoints)} checkpoints from {video} -> {out_dir}")
    print(f"1. Open each checkpoint_NN_*.jpg and count the people ({COUNTING_RULE[:60]}...).")
    print(f"2. Fill in each \"expected_visible_people\" in {os.path.relpath(gt_path, ROOT)}.")
    print("3. Score it:")
    print(f"   python scripts/benchmark/benchmark_tracking.py {video} --ground-truth {os.path.relpath(gt_path, ROOT)} "
          f"--process-fps 8 --save-checkpoints {os.path.relpath(out_dir, ROOT)}/scored")


if __name__ == "__main__":
    main()
