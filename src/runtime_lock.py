"""Cross-process singleton guard for EdgeSight writers sharing one store database."""
from __future__ import annotations

import os
import hashlib
from pathlib import Path
from typing import TextIO


def _lock_path(db_path: str, store_id: str | None = None) -> Path:
    database = Path(db_path).expanduser().resolve()
    if store_id:
        # Store identity is stable across native/Docker database mount paths.
        key = hashlib.sha256(str(store_id).encode("utf-8")).hexdigest()
        # Keep this beside the shared DB so host and container writers see the
        # same lock inode through the shared storage mount.
        root = database.parent / ".runtime-locks"
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{key}.lock"
    database.parent.mkdir(parents=True, exist_ok=True)
    return Path(f"{database}.runtime.lock")


def acquire_runtime_lock(db_path: str, store_id: str | None = None) -> TextIO:
    """Acquire a non-blocking OS file lock adjacent to ``db_path``.

    Returns an open file object that must stay alive for the EdgeSight process lifetime.
    OS releases the flock automatically on process exit/crash.
    """
    from fcntl import LOCK_EX, LOCK_NB, flock

    database = Path(db_path).expanduser().resolve()
    lock_path = _lock_path(str(database), store_id)
    handle = lock_path.open("a+")
    try:
        flock(handle.fileno(), LOCK_EX | LOCK_NB)
    except BlockingIOError as exc:
        handle.seek(0)
        owner = handle.read().strip() or "unknown process"
        handle.close()
        identity = f"store {store_id}" if store_id else str(database)
        raise RuntimeError(f"EdgeSight writer already active for {identity} ({owner})") from exc

    handle.seek(0)
    handle.truncate()
    handle.write(f"pid={os.getpid()}\n")
    handle.flush()
    return handle


def runtime_lock_is_held(db_path: str, store_id: str | None = None) -> bool:
    """Probe whether a live edge already owns the database lock, without waiting."""
    from fcntl import LOCK_EX, LOCK_NB, LOCK_UN, flock

    database = Path(db_path).expanduser().resolve()
    lock_path = _lock_path(str(database), store_id)
    handle = lock_path.open("a+")
    try:
        try:
            flock(handle.fileno(), LOCK_EX | LOCK_NB)
        except BlockingIOError:
            return True
        flock(handle.fileno(), LOCK_UN)
        return False
    finally:
        handle.close()
