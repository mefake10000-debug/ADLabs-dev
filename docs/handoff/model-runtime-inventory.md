# Model runtime inventory — review branch

Observed 2026-10-24 from `configs/pipeline.yaml`, `src/perception/registry.py`, `src/perception/model_stack.py`, and the checked-in `models/` tree. No inference worker was started for this audit. No model weights are committed in this review branch, and Docker is not accessible from this environment. Thus “loaded” and “called” are **No in this audit session**, regardless of registry/config availability.

| Model or capability | Implementation | Configured weight path | Configured / enabled | Loaded / called here | Lane and consumer | Evidence / limitation |
|---|---|---|---|---|---|---|
| YOLO26s people detector | `src/perception/detector.py`, `src/perception/registry.py` | `models/yolo26s.pt` | Selected in `configs/pipeline.yaml`; constructed only inside an explicitly started worker | No / No | Critical person-detection lane; feeds ByteTrack, tripwires, zones, queues | File absent from the committed `models/` tree. No FPS or accuracy measured here. |
| RF-DETR | `src/perception/detector_backend.py`, `src/perception/detector.py` | Variant-dependent `models/pack/01-detection/rfdetr/` files | Opt-in backend; off unless explicitly selected | No / No | Alternate person detector | Pack contains guidance stubs, not weights. Not a simultaneous second detector by default. |
| OSNet ReID | `src/perception/reid.py`, `src/perception/registry.py` | `models/pack/03-reid/osnet_x0_25_msmt17.onnx` or configured `.pth` | `models.reid.enabled: true`, but master enrichment switch `models.enabled: false`; quality/session gated | No / No | Optional slow lane; session-scoped association when wired and artifacts exist | No matching weight file in this branch. No cross-camera identity accuracy evidence. |
| CLIP ViT-B/32 | `src/perception/model_stack.py` and product/category adapters | `weights/clip/ViT-B-32.pt` | Product/enrichment master switch off; no separate every-frame call | No / No | Optional category-interest enrichment | No weight file in this branch; categories are not SKU/sales evidence. |
| RTMPose-t/s | `src/perception/rtmpose_estimator.py` | `models/pack/02-tracking/` or configured ONNX | Conditional on estimator flag and weight availability | No / No | Slow pose lane; foot-point refinement | No ONNX weights in this branch. Pose/detection association is unscored. |
| Shelf-gap geometry (“SelfCap” in the owner’s shorthand) | `src/analytics/shelf_gap_geometry.py` | None | Code path exists; upstream product detections are disabled by default | No / No | Optional shelf/display gap summary | This is geometry over product boxes, not a separate learned “SelfCap” model; no planogram or shelf labels. |
| MiVOLO v2 age/gender | `src/perception/model_stack.py`; gated adapter/catalog entry | `models/pack/08-demographics/mivolo_v2/model.safetensors` | GATED; master enrichment off and privacy/DPIA gate applies | No / No | Optional aggregate demographics only | No weights, no approved DPIA/labels, no measured output. Do not enable or display as live. |

## Run-state meaning

- `configs/pipeline.yaml` selects YOLO26s for the detector when a worker is explicitly started. The worker is not running in this audit.
- Compose starts a lightweight supervisor and local API/dashboard services, but the supervisor does not open video or load models. Its Start operation must receive explicit configured camera IDs and required secrets.
- `configs/cameras.yaml` currently points at a local `restaurant_ch17` clip that is excluded from Git. Since that file is not present in the candidate tree, Start will report it missing until the operator selects an available permitted source.
- `models.enabled` is `false`; the slow enrichment models are therefore off by default. A configured or registered entry is not proof of a loaded model.
- No weights were added, downloaded, or removed. Keep weights outside Git and mount them read-only for the supervisor/worker deployment.
- No measured per-model cost, backend, feed FPS, inference FPS, effective FPS, or accuracy is available for this review run.
