# Competitor parity — field stubs (EdgeSight)



Companion to `docs/research/competitor-parity-auki-shire-neurospot.md`.

Maps portal Intelligence-parity cards → real `/api/v1/live` keys. Empty/null → PARTIAL/NO-DATA — never fabricate.



| Card | LIVE fields today | PARTIAL / next | FUTURE / BLOCKED |

|------|-------------------|----------------|------------------|

| Entrance / stop | `total_visitors`, tripwire counts | `engagement.engaged_ratio` when enrichment off | — |

| Floor / traction | `dwell_zones[]`, heatmap JPEG | Zone path graph | Spatial twin |

| Queue timestamps | `queue_length`, `avg_queue_wait_seconds`, `queue_alert_active` | `queues[].join_ts` / leave episodes | POS abandon $ |

| Staffing | `staff_now`, staff zone occupancy | `response_time_to_queue` | Spatial AR tasks |

| Safety | `queue_alert_active` | Alerts catalog heuristics | FR / weapons (BLOCKED) |

| Shelf / retail | `products_top[]` when models loaded | Fixture-id interest | Closed-set SKU / planogram API |

| Display interest | `products_top`, `engagement.*` | Facing≠footfall attention map | — |

| Store compare | — | — | Multi-store rollups |

| Alerts | queue alert flag | Role-routed inbox | Partner POS |

| Spatial twin / AR | — | — | Optional Auki posemesh (partner) |



Privacy (unchanged): YuNet redaction; session OSNet ReID only; no facial identity; demographics k-anon.
