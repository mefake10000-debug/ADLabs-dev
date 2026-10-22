# CLIP ViT-B-32 (text encoder for YOLO-World)

| | |
|--|--|
| **Location** | `repos/ADLabs-dev/weights/clip/ViT-B-32.pt` (~338MB) — **not duplicated** here |
| **Why segregated pointer** | Avoid a second 338MB copy in `pack/`; Docker mounts `./weights` |
| **Role** | Open-vocab product / shelf category prompts via YOLO-World |
| **Wired?** | **Yes** in enrichment tier when CLIP path exists |

Do not claim SKU OCR or pupil gaze from CLIP.
