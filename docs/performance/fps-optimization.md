# Live FPS scheduling and measurement

EdgeSight separates the video feed rate, person-detector rate, and overlay output rate. The per-camera `perf` object in `data/storage/state/live.json` reports:

- `feed_fps`: source decode rate measured by `StreamReader`.
- `model_inference_fps`: actual person-detector calls per second.
- `effective_fps`: annotated frames successfully written per second.
- `skip_rate`: consumed frames on which the detector was skipped.
- `detector_ms_avg`: mean time spent in the person detector during the completed window.
- `motion_score` and `last_schedule_reason`: context for the most recent scheduling decision.

Rates remain `null` until their source has a measurement. The effective rate is not calculated from feed and inference rates; it is counted from successful annotated-frame writes. The website's Model Health view reads the same per-camera values, preserving nulls when EdgeSight has not measured them.

## Scheduling policy

`configs/pipeline.yaml` has an `optimization` section. `enabled` turns scheduling on, `mode` selects the motion sensitivity (`conservative`, `balanced`, or `aggressive`), `min_inference_fps` sets the minimum time-based detector cadence, `motion_threshold` controls scene-motion sensitivity, `fast_track_velocity_px_s` forces a new detector pass for a fast-moving tracked person, and `use_prediction` enables short prediction overlays between real detections. Stationary tracks can use the longer frame cadence allowed by the minimum-rate floor. `adaptive_slow_tier` allows expensive CPU enrichment to back off when the scene is active. The current default is balanced scheduling with a 5 FPS inference floor and a 0.4-second prediction horizon.

The detector is always called on startup, when the tracker has no tracks, during a scene change or high-motion interval, when a track is new/missed/recovering, and when the minimum-rate deadline arrives. A tiny 160×90 grayscale difference is used only for scheduling. If image-difference analysis is unavailable, the scheduler chooses inference.

Track velocity produces copied, short-lived overlay views. The overlay labels these as `PREDICTED`; predicted views never update tracker state or feed entrance counts, zone dwell, queue metrics, heatmaps, or tripwire crossings. Those metrics advance only on real detections. CPU-heavy enrichment remains serialized and runs on its existing cadence; high motion can reduce its refresh frequency to protect person detection.

Detector calls run in a per-camera worker with a one-frame pending slot. If the worker is occupied, the pending frame is replaced with the latest camera image instead of building a backlog. A shared lock serializes calls to the shared detector across cameras, while the main loop continues rendering each decoded frame and owns tracker/analytics updates. This bounds queued memory and avoids concurrent MPS entry. When the detector is on CPU, enrichment shares the detector lock to avoid CPU model-pool oversubscription; when detection is on MPS, slow enrichment stays on CPU and may overlap safely.

## Model audit for this branch

The active fast-path candidate is the already-present `models/yolo26s.pt`. The existing slow tier can load `models/yolo26m-pose.pt`, YuNet face detection, age/gender ONNX, and the existing YOLO-World product model when configured and available. These are not added or downloaded by this change. The light head-pose estimator is code, not another model. OSNet is registered/load-attempted for status but has no embedding inference consumer and its weight is absent locally. CLIP and shelf-gap detection are disabled; RF-DETR is not in the current active path. See `src/perception/registry.py` and the `models` block in `configs/pipeline.yaml` for registry/config state.

## Baseline and limits

The earlier isolated 45-frame detector+tracker baseline measured 10.03 detector FPS on MPS, 99.5 ms average detector latency (97.2 ms median), and 0.13 ms average tracker update. In the current runtime, the model selected CPU rather than MPS. A comparable 75-frame CPU run on the bundled restaurant clip measured 5.98 rendered FPS when each detector call blocked the render loop. With the bounded asynchronous worker and scheduler, it measured 14.0 rendered FPS, 7.0 detector calls/sec, 53.6% skipped frames, and 117.9 ms average detector latency. Both CPU measurements included threaded decode and overlay composition but excluded JPEG output and slow-tier model inference; the 14 FPS result is a fast-tier result, not a full-stack result. The clip source was configured for 15 FPS and delivered about 13.9 FPS in this run. MPS and CPU results are not directly comparable. This scheduler cannot make a detector run faster than its measured model/backend latency, and full-stack 15 FPS remains hardware- and scene-dependent.

CPU monitoring uses the existing optional `psutil` process sampler. This is process CPU, not a GPU-utilization measurement. Privacy behavior is unchanged: raw frames and face details are not added to telemetry or live state.
