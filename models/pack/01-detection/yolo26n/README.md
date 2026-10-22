# YOLO26n — doorway fast tier

**Weight:** `yolo26n.pt` (this folder)  
**Dossier:** `../../to-integrate/yolo26n-doorway-tier.md` (sibling under `models/`)  
**Role:** Narrow doorway / entrance counting with lower recall than yolo26s — more cams per edge box.

## Use with EdgeSight

- Prefer keeping production floor cams on `models/yolo26s.pt`.  
- Point doorway cameras at `/app/models/pack/01-detection/yolo26n.pt` (Docker mount) via per-cam `perception.model_name` when wired.  
- **Not production-default** until re-benchmarked on pilot doorway clips.

## Source

https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt
