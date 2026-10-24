# Multi-camera synchronization and deduplicated occupancy

## What “synchronized” means here

Three separate capabilities are required. One model cannot solve all three:

1. **Capture-time alignment:** each frame carries edge wall time and monotonic receive time. The fusion worker compares the same-host monotonic receive time in a short window. This aligns when the edge received/decoded a frame, not the camera exposure instant; RTSP buffering and camera clock phase are not verified.
2. **Floor/zone alignment:** an operator marks the *same physical zone* with the same `store_zone_id` in each camera, then calibrates each camera's 3×3 `floor_homography` into the same store-floor coordinate system.
3. **Identity association:** local ByteTrack IDs are camera-specific. Session-scoped OSNet body embeddings can associate two local tracklets only when the shared-zone, time-window, cosine-similarity, and projected-floor-distance gates all pass.

The detector/tracker remain per camera (YOLO26n/RF-DETR + ByteTrack). OSNet (current model pack) is the ReID model. The shared-zone graph, homography projection, cosine comparison, and union-counting are deterministic code, not another learned model. Pose can improve foot-point/occlusion handling later; it is not required for the first association gate. Face recognition, CLIP, SAM, and LocateAnything are not synchronization tools.

## Configuration and fail-closed gates

Each camera zone may include a `store_zone_id`; the same value means the zones overlap in the *physical store*, not merely that they share a label. The camera config may include `floor_homography` mapping pixels to the same floor coordinates. The operator calibrates these values through `/api/v1/config/cameras/{camera_id}/calibration`.

Pixel-space tripwires, zones, glass ROIs, and floor homographies are now saved in a local calibration table under a one-way hash of the source URL/path. Switching a camera to a different video clears those pixel geometries; switching back restores only that source's own geometry. RTSP credentials are not copied into this calibration table.

`configs/pipeline.yaml` has `cross_camera_fusion.enabled: false` by default. Fusion remains gated unless:

- fusion is explicitly enabled;
- ReID is loaded and active;
- at least one store-zone ID is mapped in two or more cameras; and
- every camera in those shared-zone groups has a valid homography.

An uncalibrated camera continues to report its own occupancy. It is never silently merged or dropped. The owner-facing `/api/v1/floor-view` reports camera freshness, per-camera pixel polygons, shared-zone coverage, calibration state, and only reports deduplicated zone occupancy after fusion is active.

## Counting semantics

- Before calibration, `occupancy_mode: sum` is explicit; overlapping views can double-count.
- With fusion active, current track IDs are unioned only inside configured shared zones. Unmatched tracks remain separate (conservative fallback), so misses do not reduce occupancy. The response exposes `matched_active_tracks`, `unmatched_active_tracks`, and per-zone coverage so an operator can see when fusion is partial.
- Global IDs and embeddings stay in process memory and expire after the configured TTL. They are not serialized to snapshots, telemetry events, or database rows. Sample-video loop boundaries clear the fusion gallery.

## Operator view and latency

The live screen keeps each camera angle available as its own MJPEG tile and shows per-camera freshness/FPS. The camera-collaboration panel reports whether views are independent, mapped-but-not-fused, or fused. Once floor homographies exist, `/api/v1/floor-view` provides the data to draw one store-floor outline with the camera polygons overlaid and a union count in shared zones.

The displayed timestamp is the edge receive/decode time. It is a live-ish operations view with frame/analytics lag, not synchronized multi-camera playback. Do not label it “frame perfect” or “camera exposure synchronized” until capture-clock/PTP evidence exists.

## Current state in this repository

The two sample camera feeds have independent pixel calibrations, no verified common `store_zone_id` assignment, and no floor homographies. Fusion is therefore correctly **GATED**; the sample clips are not evidence that two cameras saw the same people. In the current runtime, `checkout_sample.mp4` renders a color-bar test pattern rather than people, so it validates the second decoder/overlay only—not ReID or overlap deduplication. Replace it with a real second-angle recording, calibrate with known floor points, and test a synchronized overlapping segment before enabling fusion.

The unit tests cover the algorithmic gates (same-zone match, time/similarity/floor rejection, homography projection, and aggregate union) with synthetic vectors. They do not claim production precision on real store footage.
