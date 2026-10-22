import threading
from dataclasses import dataclass
from typing import Any, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None


@dataclass(frozen=True)
class FrameStamp:
    """Per-frame capture times for analytics and future multi-cam association.

    ``utc`` is host wall clock (``time.time()``) — treat as NTP-synced only when
    the edge host runs chrony/systemd-timesyncd (ops concern; see health.clock_sync).
    ``mono`` is ``time.monotonic()`` for interval math immune to wall-clock steps.
    """

    utc: float
    mono: float

    @property
    def timestamp(self) -> float:
        """Backward-compatible alias used by tracker / tripwire (wall clock)."""
        return self.utc


class FrameBuffer:
    """Thread-safe ring buffer with drop-oldest policy to avoid latency accumulation."""

    def __init__(self, maxsize: int = 5):
        self.maxsize = maxsize
        self._queue = []
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def put(self, frame_idx: int, stamp: FrameStamp, frame: Any):
        with self._lock:
            if len(self._queue) >= self.maxsize:
                self._queue.pop(0)
            self._queue.append((frame_idx, stamp, frame))
            self._not_empty.notify()

    def get(self, timeout: Optional[float] = 1.0) -> Optional[Tuple[int, FrameStamp, Any]]:
        """Returns the NEWEST buffered frame and discards anything older."""
        with self._not_empty:
            if not self._queue:
                if not self._not_empty.wait(timeout):
                    return None
            if self._queue:
                item = self._queue[-1]
                self._queue.clear()
                return item
            return None

    def clear(self):
        with self._lock:
            self._queue.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._queue)
