import cv2
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.detector import PersonDetector
from src.perception.tracker import SimpleByteTracker
from src.analytics.tripwire import Tripwire

def test_video_counting(video_path: str, max_frames: int = 400):
    print(f"Testing video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open {video_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    print(f"Resolution: {width}x{height}, FPS: {fps:.1f}")

    detector = PersonDetector(model_name="models/yolo26n.pt", conf_thresh=0.3)
    tracker = SimpleByteTracker(max_age=20, iou_threshold=0.25)

    # In this retail camera:
    # The entrance doorway is at the bottom-right (black doormat area).
    # People enter from the bottom-right and walk towards the center/top (decreasing y).
    # People exit by walking from center/top towards the bottom-right doorway (increasing y).
    # Tripwire line across the doorway: from (600, 600) to (1050, 600)
    tripwire = Tripwire(
        wire_id="tw_entrance",
        name="Main Entrance Mat",
        line=[[600, 580], [1050, 580]],
        in_direction="bottom_to_top"
    )

    frame_idx = 0
    t0 = time.time()
    while frame_idx < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        current_time = t0 + (frame_idx / fps)

        dets = detector.detect(frame)
        tracks = tracker.update(dets, current_time)
        tripwire.update(tracks, current_time)

        if frame_idx % 45 == 0:
            counts = tripwire.get_counts()
            print(f"[Frame {frame_idx:04d}] Active Tracks: {len(tracks)} | IN: {counts['in_count']}, OUT: {counts['out_count']}")

    cap.release()
    final_counts = tripwire.get_counts()
    print("\n=== FINAL TEST RESULTS ===")
    print(f"Total Frames Processed: {frame_idx}")
    print(f"IN (Entered Store):     {final_counts['in_count']}")
    print(f"OUT (Exited Store):    {final_counts['out_count']}")
    print("==========================")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_videos/entrance_sample.mp4"
    test_video_counting(path)

