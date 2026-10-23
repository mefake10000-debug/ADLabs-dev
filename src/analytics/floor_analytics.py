"""Floor paths, zone sequences, and traction scores from session tracks.

Session-scoped track IDs only — no cross-day / cross-camera identity.
Paths are in-memory rings; durable emit happens on track retire (caller).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from src.analytics.zones import Zone
from src.perception.tracker import Track


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + "Z"


class FloorAnalytics:
    def __init__(
        self,
        sample_interval_seconds: float = 0.25,
        min_displacement_frac: float = 0.003,
        max_points_per_track: int = 240,
        route_min_zones: int = 2,
        revisit_merge_seconds: float = 1.5,
        traction_window_seconds: float = 900.0,
        frame_wh: Optional[Tuple[float, float]] = None,
    ):
        self.sample_interval_seconds = sample_interval_seconds
        self.min_displacement_frac = min_displacement_frac
        self.max_points_per_track = max_points_per_track
        self.route_min_zones = route_min_zones
        self.revisit_merge_seconds = revisit_merge_seconds
        self.traction_window_seconds = traction_window_seconds
        self.frame_w = float(frame_wh[0]) if frame_wh else 1270.0
        self.frame_h = float(frame_wh[1]) if frame_wh else 720.0
        self.min_dim = min(self.frame_w, self.frame_h)

        self._paths: Dict[int, Deque[Dict[str, Any]]] = {}
        self._path_meta: Dict[int, Dict[str, Any]] = {}
        self._zone_seq: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self._open_zone: Dict[int, Dict[str, Any]] = {}  # tid -> {zone_id, enter_at}
        # closed episodes: (zone_id, track_id, enter, exit, dwell)
        self._episodes: Deque[Tuple[str, int, float, float, float]] = deque(maxlen=5000)
        self._route_counts: Dict[str, int] = defaultdict(int)

    def set_frame_size(self, w: float, h: float):
        self.frame_w, self.frame_h = float(w), float(h)
        self.min_dim = min(self.frame_w, self.frame_h)

    def update(self, tracks: List[Track], zones: List[Zone], current_time: float):
        active_ids = {t.track_id for t in tracks}
        min_disp = self.min_displacement_frac * self.min_dim

        for track in tracks:
            tid = track.track_id
            fx, fy = track.foot_point
            nx, ny = fx / self.frame_w, fy / self.frame_h
            ring = self._paths.setdefault(tid, deque(maxlen=self.max_points_per_track))
            meta = self._path_meta.setdefault(
                tid, {"started_at": current_time, "last_t": 0.0, "last_xy": None}
            )
            last_xy = meta["last_xy"]
            dt = current_time - meta["last_t"]
            moved = True
            if last_xy is not None:
                dx = fx - last_xy[0]
                dy = fy - last_xy[1]
                moved = (dx * dx + dy * dy) ** 0.5 >= min_disp
            if moved or dt >= self.sample_interval_seconds:
                ring.append({"t": _iso(current_time), "x": round(nx, 4), "y": round(ny, 4)})
                meta["last_t"] = current_time
                meta["last_xy"] = (fx, fy)

            # Zone membership for sequence
            inside_id = None
            for z in zones:
                if tid in z.active_tracks_in_zone:
                    inside_id = z.zone_id
                    break
            open_ep = self._open_zone.get(tid)
            if inside_id and (not open_ep or open_ep["zone_id"] != inside_id):
                if open_ep:
                    self._close_zone_episode(tid, open_ep, current_time)
                self._open_zone[tid] = {"zone_id": inside_id, "enter_at": current_time}
            elif not inside_id and open_ep:
                self._close_zone_episode(tid, open_ep, current_time)
                self._open_zone.pop(tid, None)

        # Retire vanished tracks
        for tid in list(self._paths.keys()):
            if tid not in active_ids:
                open_ep = self._open_zone.pop(tid, None)
                if open_ep:
                    self._close_zone_episode(tid, open_ep, current_time)
                self._finalize_route(tid)
                self._paths.pop(tid, None)
                self._path_meta.pop(tid, None)
                self._zone_seq.pop(tid, None)

        self._prune_episodes(current_time)

    def _close_zone_episode(self, tid: int, open_ep: Dict[str, Any], now: float):
        enter = open_ep["enter_at"]
        dwell = max(0.0, now - enter)
        zone_id = open_ep["zone_id"]
        seq = self._zone_seq[tid]
        if (
            seq
            and seq[-1]["zone"] == zone_id
            and seq[-1].get("exit_at")
            and (enter - float(seq[-1]["_exit_raw"])) <= self.revisit_merge_seconds
        ):
            # merge revisit into previous run
            prev = seq[-1]
            prev["exit_at"] = _iso(now)
            prev["_exit_raw"] = now
            prev["dwell_s"] = round(prev["dwell_s"] + dwell, 2)
        else:
            seq.append({
                "zone": zone_id,
                "enter_at": _iso(enter),
                "exit_at": _iso(now),
                "dwell_s": round(dwell, 2),
                "_exit_raw": now,
                "_enter_raw": enter,
            })
        self._episodes.append((zone_id, tid, enter, now, dwell))

    def _finalize_route(self, tid: int):
        seq = self._zone_seq.get(tid) or []
        ids = []
        for ep in seq:
            if not ids or ids[-1] != ep["zone"]:
                ids.append(ep["zone"])
        if len(ids) >= self.route_min_zones:
            key = ">".join(ids)
            self._route_counts[key] += 1

    def _prune_episodes(self, now: float):
        cutoff = now - self.traction_window_seconds
        while self._episodes and self._episodes[0][3] < cutoff:
            self._episodes.popleft()

    def active_paths(self, limit: int = 12) -> List[Dict[str, Any]]:
        out = []
        for tid, ring in list(self._paths.items())[:limit]:
            meta = self._path_meta.get(tid, {})
            seq = [
                {k: v for k, v in ep.items() if not k.startswith("_")}
                for ep in self._zone_seq.get(tid, [])
            ]
            route_ids = []
            for ep in seq:
                if not route_ids or route_ids[-1] != ep["zone"]:
                    route_ids.append(ep["zone"])
            out.append({
                "track_id": tid,
                "started_at": _iso(meta.get("started_at", time.time())),
                "ended_at": None,
                "path": list(ring)[-60:],
                "zones_visited_seq": [ep["zone"] for ep in seq],
                "route_key": ">".join(route_ids) if len(route_ids) >= self.route_min_zones else None,
                "path_dwell_seconds": round(
                    time.time() - float(meta.get("started_at", time.time())), 2
                ),
            })
        return out

    def zone_traction(self, zones: List[Zone], now: float) -> List[Dict[str, Any]]:
        by_zone: Dict[str, List[Tuple[int, float, float, float]]] = defaultdict(list)
        for zone_id, tid, enter, exit_t, dwell in self._episodes:
            by_zone[zone_id].append((tid, enter, exit_t, dwell))
        # in-flight
        for tid, open_ep in self._open_zone.items():
            dwell = max(0.0, now - open_ep["enter_at"])
            by_zone[open_ep["zone_id"]].append((tid, open_ep["enter_at"], now, dwell))

        rows = []
        for z in zones:
            eps = by_zone.get(z.zone_id, [])
            tids = {e[0] for e in eps}
            u = len(tids)
            if u == 0:
                rows.append({
                    "zone_id": z.zone_id,
                    "zone_kind": getattr(z, "zone_type", "dwell"),
                    "name": z.name,
                    "U": 0,
                    "total_dwell_s": 0.0,
                    "avg_dwell_s": 0.0,
                    "revisit_rate": 0.0,
                    "traction_score": 0.0,
                    "occupancy": z.current_occupancy,
                })
                continue
            per_tid: Dict[int, float] = defaultdict(float)
            visit_counts: Dict[int, int] = defaultdict(int)
            for tid, _e, _x, dwell in eps:
                per_tid[tid] += dwell
                visit_counts[tid] += 1
            total_d = sum(per_tid.values())
            avg_d = total_d / u
            revisits = sum(1 for c in visit_counts.values() if c >= 2)
            r = revisits / u
            score = u * avg_d * r
            rows.append({
                "zone_id": z.zone_id,
                "zone_kind": getattr(z, "zone_type", "dwell"),
                "name": z.name,
                "U": u,
                "total_dwell_s": round(total_d, 1),
                "avg_dwell_s": round(avg_d, 1),
                "revisit_rate": round(r, 3),
                "traction_score": round(score, 2),
                "occupancy": z.current_occupancy,
            })
        max_score = max((r["traction_score"] for r in rows), default=0.0) or 1.0
        for r in rows:
            r["share_of_traction"] = round(r["traction_score"] / max_score, 3) if max_score else 0.0
        rows.sort(key=lambda x: x["traction_score"], reverse=True)
        return rows

    def top_routes(self, limit: int = 8) -> List[Dict[str, Any]]:
        total = sum(self._route_counts.values()) or 1
        ranked = sorted(self._route_counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [
            {
                "route_key": k,
                "count": c,
                "share_of_routes": round(c / total, 3),
                "median_path_dwell_seconds": None,  # needs settled path retire stats
            }
            for k, c in ranked
        ]

    def snapshot(self, zones: List[Zone], now: float) -> Dict[str, Any]:
        traction = self.zone_traction(zones, now)
        routes = self.top_routes()
        return {
            "window_seconds": int(self.traction_window_seconds),
            "generated_at": _iso(now),
            "paths_active": self.active_paths(),
            "zone_traction": traction,
            "top_routes": routes,
            "coverage_note": "session-cam only; no cross-day identity",
            # Paths sample from tracks whenever FloorAnalytics runs; traction needs dwell zones.
            "status": "LIVE",
            "badge_copy": None
            if zones
            else "Path polylines LIVE; zone traction empty until dwell zones are drawn — heatmap remains the aggregate traction view.",
        }
