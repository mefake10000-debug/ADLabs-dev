# Unified CV pipeline

One path from the camera to the site. Peer overlays (parallel boxes, NVIDIA
pallets, store-object rectangles, and a red foot drawn on top of all of them)
are not stacked. That stack was the live glitch.

## Path

```
Ultralytics YOLO (yolo26n, balanced)
        → ByteTrack
        → red foot  (+ optional RTMPose skeleton)
        → tripwire / zones / dwell
        → /api/v1/live  (+ one annotated MJPEG)
        → site
```

`DETECTOR_BACKEND=rfdetr` stays opt-in and still emits xyxy for the same tracker.
LocateAnything-3B, SKU-110K, and P2PNet are not downloaded (non-commercial /
academic-only).

## One annotator

| `OVERLAY_BOX_STYLE` | Person mark | Red foot as well? |
|---------------------|-------------|-------------------|
| `foot` (default) | Red ground point, short trail, faint ID | this is the mark |
| `skeleton` | Those, plus COCO bones when keypoints exist | yes |
| `nvidia` (`pallet`) | Pallet box only | no |
| `parallel` | Sheared body + footprint only | no |
| `aabb` | Axis-aligned box only | no |

Store objects are a separate thin class rectangle (`object bottle`), never a
second person pallet. People are either the red foot or one box style, not both.

The point is `track.foot_point` / `ground_point`: bbox bottom-center, or the
RTMPose ankle after `set_pose` (the trail tip is rewritten so the line and the
dot match on that frame).

## Crossings

`_update_analytics` sends `early_tracks` (at least 2 hits) to the tripwire and
confirmed customers to zones. A person who crosses and leaves before
`min_hits` still counts once. Staff IDs are removed from the line, dwell, and
the unique-visitor rollup.

`tests/test_crossing_integration.py` drives synthetic boxes through that order.

## RTMPose

Apache-2.0. Loaded when `models/pack/07-pose/rtmpose-t.onnx` (or `-s`) is
present, every `RTMPOSE_EVERY_N` frames (default 4). `ENABLE_RTMPOSE=0` leaves
the bbox foot. It does not re-detect people.

```bash
python3 scripts/download_pack_models_phase2.py --download --only rtmpose-t
```

## Live API

`/api/v1/live` carries tripwire `in_count` / `out_count`, zone dwell, and
`tracks[].ground_point` / `tracks[].foot`. `models.overlay_box_style` defaults
to `foot`. `GET /api/v1/overlay` reports the same. MJPEG:
`/api/v1/stream/{camera_id}`. The edge dashboard title is
“YOLO → ByteTrack → red foot”. The Next live pane shows that JPEG; it does
not draw a second overlay.

## Check

```bash
python3 -m unittest tests.test_crossing_integration tests.test_overlay_foot_tracking tests.test_track_tripwire_regression tests.test_pipeline_core
```
