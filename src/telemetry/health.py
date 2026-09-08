import time
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Collects runtime health telemetry for edge node and camera streams."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.start_time = time.time()

    def get_system_stats(self) -> Dict[str, Any]:
        uptime_seconds = int(time.time() - self.start_time)
        stats = {
            "device_id": self.device_id,
            "uptime_seconds": uptime_seconds,
            "timestamp": time.time()
        }

        # Check process memory if psutil available
        try:
            import psutil
            stats["cpu_percent"] = psutil.cpu_percent(interval=None)
            stats["memory_percent"] = psutil.virtual_memory().percent
        except ImportError:
            stats["cpu_percent"] = 0.0
            stats["memory_percent"] = 0.0

        return stats

