"""Transactional idempotency receipts. Caller owns commit/rollback with metric writes."""
import hashlib
import json
from fastapi import HTTPException


def init_receipts(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS telemetry_receipts (
        store_id TEXT NOT NULL, device_id TEXT NOT NULL, channel TEXT NOT NULL,
        record_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (store_id, device_id, channel, record_id))''')


def claim_record(conn, channel, item):
    if not item.record_id:
        return True  # rolling upgrades: legacy senders have no deduplication guarantee
    body = item.model_dump(exclude={'id', 'record_id'})
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    key = (item.store_id, item.device_id, channel, item.record_id)
    existing = conn.execute('''SELECT payload_hash FROM telemetry_receipts
        WHERE store_id=? AND device_id=? AND channel=? AND record_id=?''', key).fetchone()
    if existing:
        if existing[0] != digest:
            raise HTTPException(status_code=409, detail='Record identity reused with different content')
        return False
    conn.execute('''INSERT INTO telemetry_receipts
        (store_id, device_id, channel, record_id, payload_hash) VALUES (?,?,?,?,?)''', (*key, digest))
    return True
