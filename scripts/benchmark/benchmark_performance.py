import time
import sys
import os
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.detector import PersonDetector
from src.perception.tracker import SimpleByteTracker

def run_benchmark(num_frames: int = 100, width: int = 1280, height: int = 720):
    print("==================================================")
    print("   AD Labs EdgeSight - Hardware Benchmark Tool   ")
    print("==================================================")

    detector = PersonDetector(model_name="models/yolo26n.pt")
    tracker = SimpleByteTracker()

    print(f"Backend Device: {detector.device.upper()}")
    print(f"Testing Resolution: {width}x{height}")
    print(f"Benchmarking {num_frames} frames...")

    # Generate synthetic frames
    dummy_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

    # Warmup
    for _ in range(5):
        detector.detect(dummy_frame)

    # Measure
    detection_latencies = []
    tracking_latencies = []

    start_total = time.time()
    for i in range(num_frames):
        t0 = time.time()
        dets = detector.detect(dummy_frame)
        t1 = time.time()
        tracks = tracker.update(dets, t1)
        t2 = time.time()

        detection_latencies.append((t1 - t0) * 1000.0)
        tracking_latencies.append((t2 - t1) * 1000.0)

    total_time = time.time() - start_total
    avg_det_ms = np.mean(detection_latencies)
    avg_track_ms = np.mean(tracking_latencies)
    total_fps = num_frames / total_time

    print("\n--- RESULTS ---")
    print(f"Average Detection Latency: {avg_det_ms:.2f} ms")
    print(f"Average Tracking Latency:  {avg_track_ms:.2f} ms")
    print(f"Total Pipeline Throughput: {total_fps:.1f} FPS")
    print(f"Estimated 15-FPS Streams Supported per Node: {int(total_fps / 15.0)} streams")
    print("==================================================")

if __name__ == "__main__":
    run_benchmark(num_frames=50)

