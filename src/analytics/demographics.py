import logging
import time
from collections import Counter, deque
from typing import Any, Deque, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# A cohort is only publishable once this many distinct individuals fall into it.
# Below the threshold the cohort is folded into an "other" bucket, so a single
# inferred person can never be read back out of the API.
DEFAULT_K_ANONYMITY = 10


class _TrackCohort:
    """Per-track demographic state.

    The face model is run on small, upscaled crops, so a single inference is noisy --
    the same face came back as 15 and 18 on consecutive frames of the same clip. A
    running estimate per track is what makes the aggregate stable.
    """

    __slots__ = ("age", "age_band", "p_female", "samples", "last_seen")

    def __init__(self):
        self.age: Optional[float] = None
        self.age_band: Optional[str] = None
        self.p_female: Optional[float] = None
        self.samples: int = 0
        self.last_seen: float = 0.0

    def update(self, prediction: Dict[str, Any], alpha: float):
        age = float(prediction.get("age", 0))
        p_female = float(prediction.get("p_female", 0.5))
        if self.samples == 0:
            self.age = age
            self.p_female = p_female
        else:
            # Exponential moving average: recent observations dominate, which is what
            # we want when a shopper turns their head away and the face model starts
            # guessing from a partial view.
            self.age = self.age * (1.0 - alpha) + age * alpha
            self.p_female = self.p_female * (1.0 - alpha) + p_female * alpha
        self.samples += 1

    def finalise(self) -> Dict[str, Any]:
        from src.perception.age_gender import band_for_age

        age = int(round(self.age)) if self.age is not None else 0
        p_female = self.p_female if self.p_female is not None else 0.5
        return {
            "age": age,
            "age_band": band_for_age(age),
            "gender": "female" if p_female >= 0.5 else "male",
            "p_female": round(p_female, 4),
            "confidence": round(max(p_female, 1.0 - p_female), 3),
            "samples": self.samples,
        }


class DemographicsAnalyzer:
    """Aggregates face-model cohorts into publishable, k-anonymous population stats.

    What leaves this class is a *population description*, not a person: counts per age
    band and per gender, with small cohorts suppressed. There is no path from the
    output back to a face, a frame, or an individual.

    Two time horizons are combined:

      * *live* cohorts -- the people currently in frame, each with a running estimate;
      * *retired* cohorts -- people who have left. When a track ends, its finalised
        cohort is folded into a plain counter and the per-person state is deleted.

    The retirement matters for reporting, not for privacy. Counting only the people
    on screen at this instant means a store with 12 shoppers has 12 samples, split
    across 5 age bands, so no single band can clear the k=10 threshold and the API
    would never publish anything. Accumulating the retired cohorts over a rolling
    window gives a population mix that reflects the visit, which is what a retailer
    actually asks for. Only counters survive retirement -- the age, the gender and
    the track id of a departed person are discarded, so nothing is retained about an
    individual past their visit.
    """

    def __init__(
        self,
        k_anonymity: int = DEFAULT_K_ANONYMITY,
        smoothing_alpha: float = 0.35,
        window_seconds: float = 3600.0,
    ):
        self.k_anonymity = k_anonymity
        self.smoothing_alpha = smoothing_alpha
        self.window_seconds = window_seconds
        self._tracks: Dict[int, _TrackCohort] = {}
        self._counts: Counter = Counter()
        self._totals = {"observed": 0, "published": 0}
        # (retired_at, cohort) pairs, oldest first.
        self._retired: Deque[Tuple[float, Dict[str, Any]]] = deque()

    def observe(self, track_id: int, prediction: Dict[str, Any], timestamp: float = 0.0):
        """Folds one face-model result into the track's running cohort estimate."""
        if not prediction:
            return
        state = self._tracks.get(track_id)
        if state is None:
            state = _TrackCohort()
            self._tracks[track_id] = state
        state.update(prediction, self.smoothing_alpha)
        state.last_seen = timestamp

    def prune(self, active_track_ids: Iterable[int], timestamp: Optional[float] = None):
        """Drops cohort state for tracks that no longer exist.

        The departed person's finalised cohort is folded into the rolling aggregate
        and then deleted. Nothing about the individual survives this call: no age, no
        gender, no track id, no frame reference.
        """
        now = time.time() if timestamp is None else timestamp
        active: Set[int] = set(active_track_ids)
        for track_id in list(self._tracks.keys()):
            if track_id not in active:
                cohort = self._tracks[track_id].finalise()
                self._retired.append((now, cohort))
                del self._tracks[track_id]
        self._expire(now)

    def _expire(self, now: float):
        """Drops retired cohorts that fell out of the rolling window."""
        while self._retired and (now - self._retired[0][0]) > self.window_seconds:
            self._retired.popleft()

    def reset(self):
        self._tracks.clear()
        self._counts.clear()
        self._retired.clear()
        self._totals = {"observed": 0, "published": 0}

    def _publish(self, cohorts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Turns per-track cohorts into k-anonymous aggregates."""
        band_counts: Counter = Counter()
        gender_counts: Counter = Counter()
        for cohort in cohorts:
            band_counts[cohort["age_band"]] += 1
            gender_counts[cohort["gender"]] += 1

        total = len(cohorts)
        suppressed_bands = 0
        suppressed_gender = 0

        age_bands: List[Dict[str, Any]] = []
        for band, count in sorted(band_counts.items()):
            if count < self.k_anonymity:
                suppressed_bands += count
                continue
            age_bands.append({
                "band": band,
                "count": count,
                "pct": round(count / total * 100.0, 1) if total else 0.0,
            })

        genders: List[Dict[str, Any]] = []
        for gender, count in sorted(gender_counts.items()):
            if count < self.k_anonymity:
                suppressed_gender += count
                continue
            genders.append({
                "gender": gender,
                "count": count,
                "pct": round(count / total * 100.0, 1) if total else 0.0,
            })

        self._totals["observed"] = total
        self._totals["published"] = total - suppressed_bands

        published_cells = len(age_bands) + len(genders)
        return {
            "sample_size": total,
            "k_anonymity": self.k_anonymity,
            "age_bands": age_bands,
            "gender_split": genders,
            "suppressed_count": suppressed_bands,
            "suppressed_gender_count": suppressed_gender,
            "publishable": published_cells > 0,
            "window_seconds": self.window_seconds,
            "note": (
                f"cohorts below {self.k_anonymity} individuals are withheld"
                if suppressed_bands or suppressed_gender else "all cohorts meet the anonymity threshold"
            ),
        }

    def snapshot(self) -> Dict[str, Any]:
        cohorts = [state.finalise() for state in self._tracks.values() if state.samples > 0]
        cohorts.extend(cohort for _ts, cohort in self._retired)
        return self._publish(cohorts)

    def cohorts(self) -> List[Dict[str, Any]]:
        """Per-track cohort estimates (in-memory only; never persisted or exported)."""
        return [state.finalise() for state in self._tracks.values() if state.samples > 0]
