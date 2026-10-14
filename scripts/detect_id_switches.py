"""
Suspected tracker ID-switch report for a video, with no ground truth needed.

Runs the real PersonDetector -> SimpleByteTracker pipeline (settings from configs/pipeline.yaml)
over a clip and feeds every frame's tracks to IdSwitchDetector (src/analytics/id_switch.py),
which flags each place a person's ID vanished and a different ID took over where they were last
seen. Every flag is a suspicion to confirm by eye, which is what the annotated clips are for.

Usage (inside the edge container, where YOLO actually loads):
    docker compose run --rm --no-deps edge-analyzer python scripts/detect_id_switches.py \
        data/sample_videos/entrance_sample.mp4 --process-fps 3

--process-fps matters: the tracker counts in *frames* (min_hits, max_age, the stationary rule),
and the live edge analyzer only gets through ~2-4 frames/s on CPU, dropping the rest. Omit it to
see the tracker at its best (every frame); set it near the live "Infer FPS" to reproduce what the
dashboard actually shows.

--replay <run>/tracks.jsonl re-scores a previous run's tracks without YOLO, in seconds -- for trying
other --max-gap / --max-distance values on exactly the same tracks.

Output, in data/storage/id_switch_runs/<video>_<fps>_<timestamp>/:
  events.jsonl   one suspected switch per line (video time, lost -> new ID, gap, distance, bboxes)
  summary.json   run parameters and totals
  tracks.jsonl   every processed frame's tracks (input for --replay)
  event_NNN_<mm-ss>.mp4  a few seconds around the switch with every track's box and ID drawn:
                 red = the ID that was lost, green = the ID that took over. Same person in both
                 -> real switch; two different people -> false alarm.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import deque

import cv2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmark_tracking import DEFAULT_CONFIG, build_detector, build_tracker, load_pipeline_config  # noqa: E402
from src.analytics.id_switch import IdSwitchDetector  # noqa: E402

CLIP_BEFORE = 1.5  # seconds shown before the lost ID was last seen
CLIP_AFTER = 2.0   # seconds shown after the new ID appeared
RED, GREEN, OTHER = (0, 0, 255), (0, 200, 0), (0, 220, 220)


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"


def draw_clip_frame(jpeg, t, tracks, event):
    """One frame of an event clip: every track's box and ID, the two IDs in question highlighted."""
    img = cv2.imdecode(jpeg, cv2.IMREAD_COLOR)
    lost_seen_at = event["time"] - event["gap_seconds"]
    visible = set()
    for tid, bbox in tracks:
        visible.add(tid)
        if tid == event["lost_id"]:
            color, thick, label = RED, 3, f"LOST ID:{tid}"
        elif tid == event["new_id"]:
            color, thick, label = GREEN, 3, f"NEW ID:{tid}"
        else:
            color, thick, label = OTHER, 1, f"ID:{tid}"
        x1, y1, x2, y2 = (int(v) for v in bbox)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
        cv2.putText(img, label, (x1, max(55, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    if event["lost_id"] not in visible and t > lost_seen_at:
        # The lost ID is gone: keep a thin marker where it was last seen.
        x1, y1, x2, y2 = (int(v) for v in event["lost_bbox"])
        cv2.rectangle(img, (x1, y1), (x2, y2), RED, 1)
        cv2.putText(img, f"ID:{event['lost_id']} last seen here", (x1, min(img.shape[0] - 8, y2 + 18)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED, 1)
    cv2.rectangle(img, (0, 0), (img.shape[1], 40), (20, 20, 20), -1)
    cv2.putText(img, f"{mmss(t)}   ID {event['lost_id']} (red) -> ID {event['new_id']} (green)   "
                     f"switch flagged at {event['video_time']}", (12, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (255, 255, 255), 2)
    return img


def write_clip(path, frames, event):
    """frames: [(t, jpeg, [(track_id, bbox), ...]), ...] in order. Plays at the rate the tracker saw."""
    first = draw_clip_frame(frames[0][1], frames[0][0], frames[0][2], event)
    span = frames[-1][0] - frames[0][0]
    fps = max(1.0, (len(frames) - 1) / span) if span > 0 else 1.0
    h, w = first.shape[:2]
    rest = (draw_clip_frame(jpeg, t, tracks, event) for t, jpeg, tracks in frames[1:])
    if shutil.which("ffmpeg"):
        # H.264 via ffmpeg (in the edge image): ~10x smaller than OpenCV's own mp4v writer and
        # plays in any player, the browser and VS Code.
        ff = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
             "-r", f"{fps:.3f}", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
             "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", path],
            stdin=subprocess.PIPE)
        ff.stdin.write(first.tobytes())
        for img in rest:
            ff.stdin.write(img.tobytes())
        ff.stdin.close()
        ff.wait()
    else:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        writer.write(first)
        for img in rest:
            writer.write(img)
        writer.release()


class SavedTrack:
    """A track read back from tracks.jsonl -- just the fields IdSwitchDetector looks at."""

    def __init__(self, track_id, bbox, is_stationary):
        self.track_id, self.bbox, self.is_stationary = track_id, bbox, is_stationary

    @property
    def foot_point(self):
        return ((self.bbox[0] + self.bbox[2]) / 2.0, self.bbox[3])


def live_tracks(cap, fps, process_fps, detector, tracker, tracks_log):
    """Yields (frame_idx, video_time, frame, tracks) from the real detector + tracker, saving every
    processed frame's tracks so the run can be re-scored later with --replay."""
    frame_idx, next_t = 0, 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            return
        t = frame_idx / fps  # video time, so every timestamp can be found by scrubbing the clip
        if not process_fps or t >= next_t:
            next_t = t + 1.0 / process_fps if process_fps else 0.0
            tracks = tracker.update(detector.detect(frame), t)
            tracks_log.write(json.dumps({"frame": frame_idx, "t": round(t, 3), "tracks": [
                [tr.track_id] + [round(v, 1) for v in tr.bbox] + [bool(tr.is_stationary)] for tr in tracks]}) + "\n")
            yield frame_idx, t, frame, tracks
        frame_idx += 1


def replayed_tracks(cap, replay_path):
    """Same as live_tracks, but the tracks come from a previous run's tracks.jsonl; the video is only
    read for the clip frames."""
    with open(replay_path) as f:
        saved = {s["frame"]: s for s in map(json.loads, f)}
    frame_idx = 0
    while saved:
        ok, frame = cap.read()
        if not ok:
            return
        s = saved.pop(frame_idx, None)
        if s:
            yield frame_idx, s["t"], frame, [SavedTrack(tr[0], tr[1:5], tr[5]) for tr in s["tracks"]]
        frame_idx += 1


def run(video_path, process_fps=None, max_gap=5.0, max_distance=1.0, out_dir=None,
        clips=True, config_path=DEFAULT_CONFIG, replay=None, model=None):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: could not open {video_path}")
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    cfg = load_pipeline_config(config_path)

    stem = os.path.splitext(os.path.basename(video_path))[0]
    label = "replay" if replay else (f"{process_fps:g}fps" if process_fps else "allframes")
    out_dir = out_dir or os.path.join(ROOT, "data", "storage", "id_switch_runs",
                                      f"{stem}_{label}_{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out_dir, exist_ok=True)

    tracks_log = None
    if replay:
        frames = replayed_tracks(cap, replay)
    else:
        detector = build_detector(cfg, model=model)
        if detector.model is None:
            print("ERROR: YOLO did not load, so the tracks (and any switch report) would be meaningless. "
                  "Run this inside the edge container (docker compose run --rm --no-deps edge-analyzer ...).")
            return None
        tracks_log = open(os.path.join(out_dir, "tracks.jsonl"), "w")
        frames = live_tracks(cap, fps, process_fps, detector, build_tracker(cfg), tracks_log)

    switches = IdSwitchDetector(max_gap_seconds=max_gap, max_distance_heights=max_distance)
    events, unique_ids, candidate_count, processed, last_t = [], set(), 0, 0, 0.0
    # Recent frames (JPEG-compressed) with their tracks. An event is confirmed up to max_gap after it
    # happens and its clip starts up to max_gap + CLIP_BEFORE before it, so keep both spans.
    recent = deque()
    keep_seconds = 2 * max_gap + CLIP_BEFORE + 1.0
    started = time.time()
    with open(os.path.join(out_dir, "events.jsonl"), "w") as log:
        def report(event):
            if clips:
                start = event["time"] - event["gap_seconds"] - CLIP_BEFORE
                clip_frames = [f for f in recent if start <= f[0] <= event["time"] + CLIP_AFTER]
                if clip_frames:
                    name = f"event_{len(events) + 1:03d}_{event['video_time'].replace(':', '-')}.mp4"
                    write_clip(os.path.join(out_dir, name), clip_frames, event)
                    event["clip"] = name
            events.append(event)
            log.write(json.dumps(event) + "\n")

        for frame_idx, t, frame, tracks in frames:
            processed += 1
            last_t = t
            unique_ids.update(tr.track_id for tr in tracks)
            if clips:
                recent.append((t, cv2.imencode(".jpg", frame)[1], [(tr.track_id, list(tr.bbox)) for tr in tracks]))
                while recent[0][0] < t - keep_seconds:
                    recent.popleft()
            confirmed = switches.update(tracks, t)
            for cand in switches.new_candidates:
                candidate_count += 1
                cand["frame"], cand["video_time"] = frame_idx, mmss(t)
            for event in confirmed:
                report(event)
        for event in switches.flush():
            report(event)
    cap.release()
    if tracks_log:
        tracks_log.close()

    summary = {
        "video": video_path,
        "video_fps": round(fps, 2),
        "process_fps": f"replay of {replay}" if replay else (process_fps or "all frames"),
        "frames_processed": processed,
        "footage_seconds": round(last_t, 1),
        "wall_clock_seconds": round(time.time() - started, 1),
        "unique_track_ids": len(unique_ids),
        "candidates": candidate_count,
        "withdrawn_two_people": switches.retracted,
        "suspected_switches": len(events),
        "new_id_switches": sum(e["kind"] == "new_id" for e in events),
        "id_reused_switches": sum(e["kind"] == "id_reused" for e in events),
        "params": {"max_gap_seconds": max_gap, "max_distance_heights": max_distance,
                   "tracking": cfg.get("tracking", {})},
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("=" * 78)
    print(f"Video: {video_path}  ({summary['footage_seconds']}s, {processed} frames, "
          f"{summary['process_fps']}, {summary['wall_clock_seconds']}s wall clock)")
    print(f"Unique track IDs: {len(unique_ids)}   Suspected ID switches: {len(events)} "
          f"({summary['new_id_switches']} new-ID, {summary['id_reused_switches']} ID-reused; "
          f"{switches.retracted} of {candidate_count} candidates withdrawn as two different people)")
    print()
    print("  time    | lost -> new | kind      | gap(s) | dist (x height) | lost was still")
    for e in events:
        print(f"  {e['video_time']:7} | {e['lost_id']:>4} -> {e['new_id']:<4} | {e['kind']:9} | "
              f"{e['gap_seconds']:6} | {e['distance_heights']:15} | {e['lost_was_stationary']}")
    print()
    print(f"Report written to {out_dir}")
    print("=" * 78)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video")
    parser.add_argument("--process-fps", type=float, default=None,
                        help="Process frames at this rate to mimic the live analyzer (default: every frame)")
    parser.add_argument("--max-gap", type=float, default=5.0,
                        help="Seconds an ID may be gone and still count; also how long a candidate waits "
                             "to be confirmed")
    parser.add_argument("--max-distance", type=float, default=1.0,
                        help="Max distance between lost and new ID, in lost person's bbox heights")
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--no-clips", action="store_true", help="Skip the per-event annotated clips")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--replay", metavar="TRACKS_JSONL", default=None,
                        help="Re-score a previous run's tracks.jsonl instead of running YOLO")
    parser.add_argument("--model", default=None, help="Override perception.model_name, e.g. models/yolo26n.pt")
    args = parser.parse_args()
    result = run(args.video, args.process_fps, args.max_gap, args.max_distance, args.out_dir,
                 not args.no_clips, args.config, args.replay, args.model)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
