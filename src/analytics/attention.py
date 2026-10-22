import logging
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# An attention score above this counts as "engaged with what is in front of them".
ENGAGED_THRESHOLD = 0.55


class _AttentionState:
    __slots__ = (
        "samples", "attention_sum", "facing_samples", "phone_samples",
        "engaged_seconds", "distracted_seconds", "last_timestamp", "last_in_zone",
    )

    def __init__(self):
        self.samples = 0
        self.attention_sum = 0.0
        self.facing_samples = 0
        self.phone_samples = 0
        self.engaged_seconds = 0.0
        self.distracted_seconds = 0.0
        self.last_timestamp: Optional[float] = None
        self.last_in_zone = False


class AttentionAnalyzer:
    """Turns head orientation and body behaviour into engagement analytics.

    "Engagement" here means *the shopper is attending the space they are standing in*,
    which is the commercially useful signal: someone who has stopped, faces forward and
    is not on their phone is a candidate for merchandising, staff attention or a
    conversion prompt. Someone scrolling is not.

    The signal is a blend of:
      * head pose (how squarely the subject faces the camera plane),
      * phone use (a wrist at head height),
      * dwell (how long they have been in the zone).
    """

    def __init__(self, engaged_threshold: float = ENGAGED_THRESHOLD):
        self.engaged_threshold = engaged_threshold
        self._tracks: Dict[int, _AttentionState] = {}

    def observe(
        self,
        track_id: int,
        timestamp: float,
        attention_score: Optional[float] = None,
        facing_camera: Optional[bool] = None,
        phone_in_hand: Optional[bool] = None,
        in_zone: bool = False,
    ):
        state = self._tracks.get(track_id)
        if state is None:
            state = _AttentionState()
            self._tracks[track_id] = state

        dt = 0.0
        if state.last_timestamp is not None and timestamp > state.last_timestamp:
            dt = timestamp - state.last_timestamp

        if dt > 0 and state.last_in_zone:
            # Attribute the elapsed time to engaged or distracted using the last
            # attention reading we had.
            if state.attention_sum / max(1, state.samples) >= self.engaged_threshold:
                state.engaged_seconds += dt
            else:
                state.distracted_seconds += dt

        if attention_score is not None:
            state.samples += 1
            state.attention_sum += float(attention_score)
        if facing_camera:
            state.facing_samples += 1
        if phone_in_hand:
            state.phone_samples += 1

        state.last_timestamp = timestamp
        state.last_in_zone = in_zone

    def prune(self, active_track_ids: Iterable[int]):
        active = set(active_track_ids)
        for tid in list(self._tracks.keys()):
            if tid not in active:
                del self._tracks[tid]

    def reset(self):
        self._tracks.clear()

    def snapshot(self) -> Dict[str, Any]:
        states = list(self._tracks.values())
        tracked = len(states)
        total_samples = sum(s.samples for s in states)
        avg_attention = (
            sum(s.attention_sum for s in states) / total_samples if total_samples else 0.0
        )
        facing_samples = sum(s.facing_samples for s in states)
        phone_samples = sum(s.phone_samples for s in states)
        engaged_seconds = sum(s.engaged_seconds for s in states)
        distracted_seconds = sum(s.distracted_seconds for s in states)
        zone_seconds = engaged_seconds + distracted_seconds

        phone_users = sum(1 for s in states if s.phone_samples > 0)

        return {
            "tracked_people": tracked,
            "avg_attention_score": round(avg_attention, 3),
            "facing_ratio": round(facing_samples / total_samples, 3) if total_samples else 0.0,
            "phone_user_count": phone_users,
            "phone_usage_rate": round(phone_users / tracked, 3) if tracked else 0.0,
            "engaged_seconds": round(engaged_seconds, 1),
            "distracted_seconds": round(distracted_seconds, 1),
            "engaged_ratio": round(engaged_seconds / zone_seconds, 3) if zone_seconds else 0.0,
            "avg_engaged_dwell_seconds": round(engaged_seconds / tracked, 1) if tracked else 0.0,
            "engaged_threshold": self.engaged_threshold,
        }
