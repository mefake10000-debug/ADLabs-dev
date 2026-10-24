# Model inventory and runtime relevance

Configuration flags describe requested capabilities; they do not prove that weights exist, a model loaded, or inference ran. In the clean feature baseline `models/` contains only `.gitkeep`; no weight artifact was present. Therefore every model is unloaded and has zero inference calls while processing is OFF. Start checks that at least one configured required person-detector weight exists before spawning the worker. The original dirty checkout has additional local weights described in the evaluation handoff; they were not copied into this branch.

| Capability | Implementation/config | Configured artifact | Config enabled | Current actual status / consumer |
|---|---|---|---|---|
| Person detection | `src/perception/detector.py`, `configs/pipeline.yaml:perception` | `models/yolo26s.pt`, fallback `models/pack/01-detection/yolo11s.pt` | Required | No files in this branch; Start rejects the session before worker creation until one configured detector artifact exists. Primary detector, then ByteTrack/counting. |
| Pose | `src/perception/pose_estimator.py`, `models.pose` | `models/yolo26m-pose.pt` | Yes | No file present; slow-tier enrichment consumer. |
| Face detection | `src/perception/face_detector.py`, `models.face` | YuNet ONNX paths in config | Yes | No file present; face-local attribute pipeline, not identity recognition. |
| Age/gender attributes | `src/perception/age_gender.py`, `models.demographics` | INT8 ONNX preferred, FP32 fallback | Yes | No file present; aggregate output is k-anonymity gated. |
| Product/category interest | `src/perception/world_detector.py`, `models.products` | YOLOv8s World v2 paths in config | Yes | No file present; slow-tier interest consumer. |
| OSNet ReID | `src/perception/registry.py`, `models.reid` | OSNet ONNX then configured alias | Yes | No file present; registry capability only, no embedding/gallery consumer in this pipeline. Not useful to load until that consumer exists. |
| CLIP ViT | registry and `models.clip` | `weights/clip/ViT-B-32.pt` | No | Disabled; no active consumer. |
| Shelf YOLOE | registry and `models.shelf` | `models/pack/06-shelf/yoloe-v8s-seg-pf.pt` | No | Disabled; planogram consumer absent. |
| Head pose | `src/perception/head_pose.py`, `models.head_pose` | No weight file | Yes | Geometry-based calculation, not a separate learned checkpoint. |

No model was downloaded or silently enabled. Existing configuration keeps person detection/tracking at the fast tier and enrichment at `interval_frames: 8`; they do not all infer on every frame. The current container image is CPU-only by default. Native MPS performance has not been measured in this worktree.
