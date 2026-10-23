# Which YOLO model? Speed vs accuracy (2026-10-08)

**Short answer: switch from `yolo26m` (medium) to `yolo26s` (small).** It's at least as accurate as
medium on our footage and 2.3x faster, which also makes tracking steadier. Nano is fastest but
misses too many people.

## What was measured

All three models on `entrance_sample.mp4` (111s of real CCTV), same tracker settings, on this dev
PC: an **Intel Core i5-1235U** laptop CPU (the same chip as budget mini PCs like the Beelink EQi12),
CPU only, inside Docker on Windows. Run it yourself with `scripts/benchmark/benchmark_models.sh`.

- **Speed**: frames per second the whole pipeline (decode + detect + track) sustains.
- **People tracked**: share of the hand-counted people the tracker outputs, averaged over the 5
  hand-counted frames (each count is ±2, so a few points' difference is noise).
- **Suspected ID switches**: from `scripts/benchmark/detect_id_switches.py`, processing frames at the rate
  that model can actually sustain here -- what the live dashboard would see. Roughly half are real
  switches (`docs/models/id-switch-detector.md`), so compare them between models, don't read them as exact.

## Results

| Model | Speed here | People tracked | ID switches at that speed |
|---|---|---|---|
| Nano (`yolo26n`) | 18.8 fps | 57% | 20 |
| **Small (`yolo26s`)** | **7.9 fps** | **76%** | **17** |
| Medium (`yolo26m`, current) | 3.5 fps | 70% | 20 |

- **Small vs medium:** small finds as many people (76% vs 70% is within the counting margin) at
  2.3x the speed. At their real speeds, small also tracks better (17 vs 20 suspected switches):
  medium at 3.5 fps sees people move further between frames, which is when IDs get swapped.
- **Nano:** fastest, but tracks about one in four fewer of the people small finds (57% vs 76%).
  Possibly fine for counting at a doorway; weak for a busy floor.
- **Processing every frame** doesn't change the ranking: medium does slightly better on switches
  (15 vs 16) only when given every frame, which needs ~4x the compute we have.

## OpenVINO (Intel's inference engine) on this CPU: no gain

Small and nano exported to OpenVINO format load and run in our pipeline **without code changes**,
with the same accuracy (small: 74% vs 76%). But on this CPU they ran slightly *slower* (small 6.1
vs 7.9 fps). Published OpenVINO speedups come from Intel's **integrated GPU or NPU**, which Docker
on Windows can't reach -- so the gain has to be measured on the actual pilot box
(`docs/architecture/edge-hardware.md`).

## What this means

- **Done:** the pipeline now uses the small model (`perception.model_name: "models/yolo26s.pt"` in
  `configs/pipeline.yaml`, switched 2026-10-14).
- **Compute target for the pilot:** small at **~8 fps per camera** -- the rate where its switch
  count stops improving (17 at 7.9 fps vs 16 at every frame). This i5 CPU manages that for **one**
  camera; two cameras need roughly double. That number drives `docs/architecture/edge-hardware.md`.
- One clip, one camera angle. Re-run `scripts/benchmark/benchmark_models.sh` on the pilot clips before
  locking the choice in.
