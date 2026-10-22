# 06-shelf

Open-vocab detection+segmentation for shelf/display audits. No public closed-set grocery-SKU weights with clean licenses exist - taxonomy via prompts.

| weight | size | license | priority | source URL(s) | purpose |
|---|---|---|---|---|---|
| `yoloe-v8s-seg-pf.pt` | ~29.8MB | AGPL-3.0 | P1 | https://github.com/ultralytics/assets/releases/download/v8.3.0/yoloe-v8s-seg-pf.pt | YOLOE small (prompt-free weights) - open-vocab product boxes+masks for shelf/planogram auditing. |

```python
from ultralytics import YOLOE or model.predict(img, prompts=...); boxes+masks per product prompt
```
