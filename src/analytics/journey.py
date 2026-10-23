"""Service-journey layout health from zone names + live traction.

Converts calibrated zone occupancy/visits into buffet-metaphor stages
(Welcome drink → … → Fruit) that also map to a retail path. No fabricated
counts — missing stages stay missing; cold marked stages flag dead_zone.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence


_DEFAULT_CONFIG_REL = os.path.join("configs", "journey_stages.json")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


@lru_cache(maxsize=4)
def load_journey_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load stage labels JSON. Cached; call clear_journey_config_cache() in tests."""
    candidates: List[str] = []
    if path:
        candidates.append(path)
    env = os.environ.get("JOURNEY_STAGES_CONFIG")
    if env:
        candidates.append(env)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates.append(os.path.join(root, _DEFAULT_CONFIG_REL))
    for p in candidates:
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("stages"):
                return data
    return {
        "schema": "adlabs.journey_stages.v1",
        "metaphor": "buffet",
        "dead_zone": {"max_occupancy": 0, "max_visits": 0, "max_avg_dwell_seconds": 0.0},
        "stages": [],
    }


def clear_journey_config_cache() -> None:
    load_journey_config.cache_clear()


def _zone_explicit_stage(zone: Dict[str, Any]) -> Optional[str]:
    for key in ("journey_stage", "stage_tag", "stage", "journey_tag"):
        val = zone.get(key)
        if isinstance(val, str) and val.strip():
            return _norm(val)
    return None


def _zone_matches_stage(zone: Dict[str, Any], stage: Dict[str, Any]) -> bool:
    explicit = _zone_explicit_stage(zone)
    stage_id = _norm(str(stage.get("id") or ""))
    if explicit and (explicit == stage_id or explicit in {_norm(t) for t in stage.get("tags") or []}):
        return True
    name = _norm(str(zone.get("name") or ""))
    zid = _norm(str(zone.get("id") or ""))
    hay = f"{name} {zid}".strip()
    if not hay:
        return False
    for tag in stage.get("tags") or []:
        t = _norm(str(tag))
        if t and t in hay:
            return True
    # Exact id as whole-word-ish token in name
    if stage_id and (stage_id == name or stage_id == zid or f" {stage_id} " in f" {hay} "):
        return True
    return False


def _zone_traction(zone: Dict[str, Any]) -> Dict[str, float]:
    occ = float(zone.get("occupancy") if zone.get("occupancy") is not None else zone.get("current_occupancy") or 0)
    visits = float(
        zone.get("visits")
        if zone.get("visits") is not None
        else zone.get("total_visits")
        if zone.get("total_visits") is not None
        else 0
    )
    dwell = float(zone.get("avg_dwell_seconds") or 0)
    # Traction proxy when FloorAnalytics share is absent: visits * (1 + dwell) + occupancy
    traction = visits * (1.0 + dwell) + occ
    return {
        "occupancy": occ,
        "visits": visits,
        "avg_dwell_seconds": dwell,
        "traction_score": round(traction, 2),
    }


def _is_cold(traction: Dict[str, float], thresholds: Dict[str, Any]) -> bool:
    max_occ = float(thresholds.get("max_occupancy", 0) or 0)
    max_visits = float(thresholds.get("max_visits", 0) or 0)
    max_dwell = float(thresholds.get("max_avg_dwell_seconds", 0) or 0)
    return (
        traction["occupancy"] <= max_occ
        and traction["visits"] <= max_visits
        and traction["avg_dwell_seconds"] <= max_dwell
    )


def build_journey_block(
    zones: Sequence[Dict[str, Any]],
    *,
    config: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Build optional `/api/v1/live.journey` from zone rows (0 defaults, no fakes)."""
    cfg = config if config is not None else load_journey_config(config_path)
    thresholds = dict(cfg.get("dead_zone") or {})
    stages_cfg: List[Dict[str, Any]] = list(cfg.get("stages") or [])
    zone_list = [z for z in zones if isinstance(z, dict)]

    stages_out: List[Dict[str, Any]] = []
    missing = 0
    dead = 0
    live_n = 0

    for stage in stages_cfg:
        matched = [z for z in zone_list if _zone_matches_stage(z, stage)]
        how = stage.get("how_to_implement") or "Draw a dwell zone and name it with this stage tag."
        base = {
            "id": stage.get("id"),
            "label": stage.get("label") or stage.get("id"),
            "retail_label": stage.get("retail_label"),
            "tags": list(stage.get("tags") or []),
            "how_to_implement": how,
            "setup_href": "/dashboard/live?panel=calib",
            "calibrated": False,
            "status": "missing",
            "dead_zone": False,
            "visits": 0,
            "occupancy": 0,
            "avg_dwell_seconds": 0.0,
            "traction_score": 0.0,
            "zone_ids": [],
            "zone_names": [],
        }
        if not matched:
            missing += 1
            stages_out.append(base)
            continue

        # Aggregate matched zones (multi-cam same stage tag)
        occ = 0.0
        visits = 0.0
        dwell_acc: List[float] = []
        ids: List[str] = []
        names: List[str] = []
        for z in matched:
            t = _zone_traction(z)
            occ += t["occupancy"]
            visits += t["visits"]
            if t["avg_dwell_seconds"] > 0:
                dwell_acc.append(t["avg_dwell_seconds"])
            zid = z.get("id") or z.get("zone_id")
            if zid:
                ids.append(str(zid))
            zn = z.get("name")
            if zn:
                names.append(str(zn))
        avg_dwell = round(sum(dwell_acc) / len(dwell_acc), 1) if dwell_acc else 0.0
        traction = {
            "occupancy": occ,
            "visits": visits,
            "avg_dwell_seconds": avg_dwell,
            "traction_score": round(visits * (1.0 + avg_dwell) + occ, 2),
        }
        cold = _is_cold(traction, thresholds)
        status = "dead_zone" if cold else "live"
        if cold:
            dead += 1
        else:
            live_n += 1
        stages_out.append({
            **base,
            "calibrated": True,
            "status": status,
            "dead_zone": cold,
            "visits": int(visits) if visits == int(visits) else round(visits, 1),
            "occupancy": int(occ) if occ == int(occ) else round(occ, 1),
            "avg_dwell_seconds": avg_dwell,
            "traction_score": traction["traction_score"],
            "zone_ids": ids,
            "zone_names": names,
        })

    return {
        "metaphor": cfg.get("metaphor") or "buffet",
        "schema": cfg.get("schema") or "adlabs.journey_stages.v1",
        "stages": stages_out,
        "summary": {
            "stage_count": len(stages_out),
            "calibrated": sum(1 for s in stages_out if s["calibrated"]),
            "missing": missing,
            "dead_zone": dead,
            "live": live_n,
        },
        "dead_zone_thresholds": {
            "max_occupancy": float(thresholds.get("max_occupancy", 0) or 0),
            "max_visits": float(thresholds.get("max_visits", 0) or 0),
            "max_avg_dwell_seconds": float(thresholds.get("max_avg_dwell_seconds", 0) or 0),
        },
        "note": (
            "Stages match zone names/tags from cameras.yaml. "
            "missing = not marked · dead_zone = marked but cold · live = visits/dwell/occupancy. "
            "Defaults are 0 — never fabricated."
        ),
    }


def zones_from_snapshot_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten zones[] from one or more live snapshot payloads."""
    out: List[Dict[str, Any]] = []
    for row in rows:
        for z in row.get("zones") or []:
            if isinstance(z, dict):
                out.append(z)
    return out
