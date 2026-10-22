"""Checks whether two threads can drive ultralytics models on MPS at the same time.

PyTorch's MPS backend keeps one Metal command buffer per device. Driving it from two
threads at once has been observed to abort the process with
`_status < MTLCommandBufferStatusCommitted`. This script reproduces it so the
enrichment tier's device strategy can be chosen on evidence rather than hope.
"""
import os
import sys
import threading
import traceback

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultralytics import YOLO

DEVICE = sys.argv[1] if len(sys.argv) > 1 else "mps"
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 30

cap = cv2.VideoCapture("data/sample_videos/entrance_sample.mp4")
ok, frame = cap.read()
cap.release()
if not ok:
    raise SystemExit("could not read the sample frame")

detector = YOLO("models/yolo26m.pt")
detector.to(DEVICE)
pose = YOLO("models/yolo26m-pose.pt")
pose.to(DEVICE)

errors = []


def run(model, tag, other):
    for _ in range(ROUNDS):
        try:
            model.predict(frame, conf=0.3, device=DEVICE, verbose=False)
        except Exception as e:
            errors.append(f"{tag}: {e}")
            return


def worker_a():
    run(detector, "detector", pose)


def worker_b():
    run(pose, "pose", detector)


print(f"device={DEVICE} rounds={ROUNDS}")
t1 = threading.Thread(target=worker_a)
t2 = threading.Thread(target=worker_b)
t1.start()
t2.start()
t1.join()
t2.join()

if errors:
    print("ERRORS:", errors)
else:
    print("completed with no exception")
print("exit status: still alive")
