import threading
from typing import Optional, Tuple, Any

try:
    import numpy as np
except ImportError:
    np = None

class FrameBuffer:
    """Thread-safe ring buffer with drop-oldest policy to avoid latency accumulation."""

    def __init__(self, maxsize: int = 5):
        self.maxsize = maxsize
        self._queue = []
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def put(self, frame_idx: int, timestamp: float, frame: Any):
        with self._lock:
            if len(self._queue) >= self.maxsize:
                # Drop oldest frame to ensure inference always operates on newest frame
                self._queue.pop(0)
            self._queue.append((frame_idx, timestamp, frame))
            self._not_empty.notify()

    def get(self, timeout: Optional[float] = 1.0) -> Optional[Tuple[int, float, Any]]:
        with self._not_empty:
            if not self._queue:
                if not self._not_empty.wait(timeout):
                    return None
            if self._queue:
                return self._queue.pop(0)
            return None

    def clear(self):
        with self._lock:
            self._queue.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._queue)
