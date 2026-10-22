# 01-detection

Person/vehicle/goods detection for consumer+retail intelligence. Feed to trackers.

| weight | size | license | priority | source URL(s) | purpose |
|---|---|---|---|---|---|
| `yolo11n.pt` | ~5.4MB | AGPL-3.0 | P0 | https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt | COCO YOLO11 nano detector (person=cls0, plus carts/vehicles/bags) - fast edge baseline. |
| `yolo11s.pt` | ~18.4MB | AGPL-3.0 | P0 | https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt | COCO YOLO11 small - primary retail detector (person, carts, boxes, chairs). |
| `yolo11m.pt` | ~38.8MB | AGPL-3.0 | P1 | https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m.pt | COCO YOLO11 medium - accuracy tier for crowded/occluded scenes (offline batch). |
| `yolo11n-pose.pt` | ~6.0MB | AGPL-3.0 | P0 | https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.pt | COCO17 keypoints - posture/pickup proxies (hand-near-shelf, stationary vs moving). |

```python
from ultralytics import YOLO; r=YOLO('models/pack/01-detection/yolo11s.pt')(frame); r.boxes.xyxy / .cls / .conf
```
