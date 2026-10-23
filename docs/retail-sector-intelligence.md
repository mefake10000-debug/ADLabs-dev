# Retail sector intelligence (EdgeSight)

Companion to the portal Live hub. Floor roles replace the retired industry vertical taxonomy (fashion NFC / restaurant tables / manufacturing conveyor / jewelry touchpoints).

## `/api/v1/live` additions

| Key | Role |
|-----|------|
| `retail_roles` | Honest floor-role maturity (`entrance` · `path` · `dwell` · `queue` · `staff` · `shelf`) |
| `nfc` | Optional hardware stub — empty until `POST /api/v1/nfc/tap` |
| `industry` | **Deprecated** alias of the old vertical map (`_deprecated: true`) |
| `entrance` | Glass stop-rate / conversion when snapshot has them (else absent → FUTURE in UI) |
| `journey` | Path stages + dead_zone / missing summary |
| `queues` / `live.queue` | Length, wait, p95 when sampled |
| `staff` / `live.staff` | Geometry coverage; response_time PARTIAL |
| `products_top` | Open-vocab shelf interest |

## NFC

Kept as a harmless webhook stub. Not featured as a Live industry tab.

```
POST /api/v1/nfc/tap
GET  /api/v1/nfc/taps
```

## Tests

`tests/test_nfc_industry.py` — empty NFC → NEEDS-HARDWARE; real POST → LIVE; `retail_roles.schema == floor_roles_v1`.

See also portal `docs/retail-sector-intelligence.md` when present.
