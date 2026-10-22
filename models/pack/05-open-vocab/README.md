# 05-open-vocab

Text-prompted detection (YOLO-World) + CLIP for zero-shot classification of products/contexts.

| weight | size | license | priority | source URL(s) | purpose |
|---|---|---|---|---|---|
| `yolov8s-worldv2.pt` | ~24.7MB | AGPL-3.0 | P0 | https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s-worldv2.pt | YOLO-World v2 small - text-prompted classes (bottle, backpack, cart, sign...) via set_classes(). |
| `yolov8l-worldv2.pt` | ~89.9MB | AGPL-3.0 | P1 | https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8l-worldv2.pt | YOLO-World v2 large - better open-vocab recall for product taxonomy (offline accuracy tier). |

```python
from ultralytics import YOLOWorld; YOLOWorld('models/pack/05-open-vocab/yolov8s-worldv2.pt').set_classes([...])
```
