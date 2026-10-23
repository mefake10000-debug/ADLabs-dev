try:
    import cv2
except ImportError:
    cv2 = None
import time
import threading
import logging
from typing import Optional, Tuple, Any
try:
    import numpy as np
except ImportError:
    np = None
from src.ingestion.frame_buffer import FrameBuffer, FrameStamp, FrameStamp

logger = logging.getLogger(__name__)

class StreamReader:
    """Threaded RTSP / video file stream reader with auto-looping and reconnect logic."""

    def __init__(self, camera_id: str, source: str, fps_target: int = 15, buffer_size: int = 5):
        self.camera_id = camera_id
        self.source = source
        self.fps_target = fps_target
        self.frame_interval = 1.0 / max(1, fps_target)
        self.buffer = FrameBuffer(maxsize=buffer_size)

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.cap: Optional[cv2.VideoCapture] = None

        self.is_file = not (source.startswith("rtsp://") or source.startswith("rtsps://") or source.startswith("http://"))
        self.fps_actual = 0.0
        self.dropped_frames = 0
        self.is_connected = False
        # Sample-video loop detection: every EOF wrap bumps this. The pipeline uses it
        # to reset per-pass counters (looping footage would otherwise inflate uniques).
        self.loop_count = 0
        self.source_fps = 0.0

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, name=f"Reader-{self.camera_id}", daemon=True)
        self.thread.start()
        logger.info(f"StreamReader started for {self.camera_id} (Source: {self.source})")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_connected = False
        logger.info(f"StreamReader stopped for {self.camera_id}")

    def _open_stream(self) -> bool:
        if self.cap:
            self.cap.release()

        # For RTSP, set transport and buffer flags
        if not self.is_file:
            # OpenCV RTSP environment flags can also be set via ffmpeg options
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        else:
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap or not self.cap.isOpened():
            logger.warning(f"Failed to open video source for {self.camera_id}: {self.source}")
            self.is_connected = False
            return False

        self.is_connected = True
        if self.is_file:
            try:
                self.source_fps = round(float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0), 2)
            except Exception:
                self.source_fps = 0.0
        logger.info(f"Successfully connected to stream: {self.camera_id}")
        return True

    def _capture_loop(self):
        frame_idx = 0
        last_frame_time = 0.0
        fps_counter = 0
        fps_timer = time.time()

        while self.running:
            if not self.is_connected:
                if not self._open_stream():
                    time.sleep(3.0)  # Reconnect backoff
                    continue

            now = time.time()
            # Throttle file playback to real-time target FPS so it doesn't rush through the video
            if self.is_file and (now - last_frame_time) < self.frame_interval:
                time.sleep(0.005)
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                if self.is_file:
                    # Loop video file continuously
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.loop_count += 1
                    logger.info(
                        f"Loop #{self.loop_count} wrapped for {self.camera_id} (sample video replays)"
                    )
                    time.sleep(0.05)
                    continue
                else:
                    logger.warning(f"RTSP stream dropped for {self.camera_id}. Attempting reconnect...")
                    self.is_connected = False
                    self.cap.release()
                    time.sleep(2.0)
                    continue

            frame_time = time.time()
            stamp = FrameStamp(utc=frame_time, mono=time.monotonic())
            last_frame_time = frame_time
            frame_idx += 1
            fps_counter += 1

            # Put frame in thread-safe buffer (utc + mono for future multi-cam windows)
            self.buffer.put(frame_idx, stamp, frame)

            # Update FPS calculations every second
            if frame_time - fps_timer >= 1.0:
                self.fps_actual = round(fps_counter / (frame_time - fps_timer), 1)
                fps_counter = 0
                fps_timer = frame_time

    def get_latest_frame(self, timeout: float = 0.5) -> Optional[Tuple[int, FrameStamp, Any]]:
        return self.buffer.get(timeout=timeout)

