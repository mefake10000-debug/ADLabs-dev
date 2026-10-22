# OSNet-x0.25 MSMT17 — soft ReID

**Weight:** `osnet_x0_25_msmt17.pt` (this folder)  
**Dossiers:** `../../../to-integrate/osnet-intra-camera-reid.md`, `osnet-cross-camera-reid.md`  
**Role:** Body-crop embeddings for ID repair / adjacent-cam handoff (privacy-gated).

## Honest constraints

- Default **off** until DPIA / product review.  
- Same-store, same-day, adjacent FOVs only — **no** face ReID, **no** multi-day gallery.  
- Needs NTP timestamps + overlap/homography gates before cross-cam linking.

## Source

https://huggingface.co/paulosantiago/osnet_x0_25_msmt17 (MSMT17 x0.25 checkpoint commonly used by tracking stacks)
