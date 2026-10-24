"""Readiness is stricter than HTTP liveness and never estimates missing signals."""
import math

MIN_FREE_BYTES = 256 * 1024 * 1024
MAX_FRAME_AGE_SECONDS = 15


def assess_readiness(snapshot, *, now, free_bytes, storage_writable=True):
    reasons = []
    frame_age = None
    if not isinstance(snapshot, dict):
        reasons.append('no_worker_snapshot')
    else:
        try:
            stamp = float(snapshot.get('frame_time'))
            age = now - stamp
            if not math.isfinite(age) or age < -2:
                reasons.append('invalid_frame_timestamp')
            else:
                frame_age = max(0, age)
                if age > MAX_FRAME_AGE_SECONDS or snapshot.get('_stale'):
                    reasons.append('stale_camera_frame')
        except (TypeError, ValueError):
            reasons.append('missing_frame_timestamp')
        try:
            fps = float(snapshot.get('infer_fps'))
            if not math.isfinite(fps) or fps <= 0:
                reasons.append('inference_not_active')
        except (TypeError, ValueError):
            reasons.append('inference_not_measured')
    if free_bytes < MIN_FREE_BYTES:
        reasons.append('low_disk_space')
    if not storage_writable:
        reasons.append('storage_not_writable')
    return {'ready': not reasons, 'reasons': reasons, 'frame_age_seconds': frame_age,
            'free_disk_bytes': free_bytes, 'minimum_free_disk_bytes': MIN_FREE_BYTES}


def read_outbox_backlog(path):
    """Observe an existing outbox without creating or migrating it from the API."""
    import os
    import sqlite3
    from urllib.parse import quote
    try:
        conn = sqlite3.connect('file:' + quote(os.path.abspath(path)) + '?mode=ro', uri=True, timeout=1)
        try:
            pending, oldest = 0, None
            for table in ('store_rollups', 'crossing_events', 'product_interest'):
                count, stamp = conn.execute(f'SELECT count(*), min(created_at) FROM {table} WHERE exported=0').fetchone()
                pending += count
                if stamp and (oldest is None or stamp < oldest):
                    oldest = stamp
            return {'pending_records': pending, 'oldest_pending_at': oldest}
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return None
