# Edge hardware for the pilot (₹25–30k)

*2026-10-19.* Prices, links and the offline-quote list live in the team's **"Pilot Edge Hardware
Options"** Google Sheet. This doc is the reasoning. **[M]** measured by us · **[V]** vendor figure ·
**[E]** our estimate.

## What the box must do

Pilot: **1 entrance camera with the live JPEG overlay** (in-store dashboard only) + **3 metrics-only
cameras**. No video leaves the store.

- **Detector:** entrance cameras need ~8 fps for tripwire counts; floor cameras (dwell, heatmap,
  occupancy) work at 3–5 fps **[M]** (`../models/model-benchmark.md`). Total **~17–32 YOLO26s detections/s**.
  Our i5 laptop CPU does 7.9/s **[M]**, so a compact box needs an AI accelerator.
- **Live overlay:** ~5–10% of one CPU core **[E]**. It does not change the hardware tier.
- **The rest is light:** ~0.8 GB RAM **[M]** (8 GB is plenty), 128–256 GB SSD (metrics only, no
  video), Gigabit Ethernet to the NVR, camera **sub-streams** (640×360, ~8 fps) to keep decoding cheap.

## Recommendation: Intel N150 mini PC + Hailo-8L M.2

- **Speed:** Hailo's Model Zoo lists YOLO26s on Hailo-8L at **67 fps (batch 1) / 147 (batch 8) [V]**,
  2–4x the pilot's need. Expect less in our pipeline **[E]**.
- **Cost:** mini PC ₹18–25k + Hailo-8L ~₹9.3k incl. GST (Mouser India) + ~₹2k parts = **₹29–37k**.
  It fits ₹30k only with the mini PC at ~₹18k (IndiaMART or offline).
- **Why:** palm-sized, ~15–25 W, x86, so Docker and Quick Sync decoding carry over. Upgrade path: a
  Hailo-8 (26 TOPS, ~₹18.6k) for 8+ cameras.
- **The catch, check before buying:** the Hailo needs an M.2 slot **wired for PCIe**. The common
  N150 8 GB/256 GB (GMKtec G3 Plus) has one PCIe slot plus one SATA-only slot, so the Hailo takes the
  PCIe slot and the system boots from a 2242 SATA SSD (~₹2k). The Beelink Mini S13 (two PCIe slots)
  is the cleanest fit but an import. **Avoid the Beelink EQ14** (Frigate docs: known compatibility
  issues).

**Ruled out:** N150 alone (~7–10/s, one camera) · Raspberry Pi 5 + AI HAT (Pi 5 8 GB now ₹17–23k in
India, no H.264 hardware decoder, ARM port) · RK3588 boards (~40–45/s, bigger port) · Jetson Orin
Nano Super (~₹70k).
**Fallback:** used Dell OptiPlex SFF + low-profile GTX 1650 (~₹22–30k). Runs today's code unchanged
(CUDA), but it's bulky and draws ~100–150 W.

## Code changes the box needs

1. **Hailo detector backend** behind the existing `detect()` (`src/perception/detector.py`,
   `docker/Dockerfile.edge`, reuse `hardware_backend` in `configs/pipeline.yaml`).
2. **Batch frames across cameras** into one detector call: ~2x on Hailo **[V]**.
3. **Per-camera `live_view: true/false`**: metrics-only cameras skip drawing and JPEG encoding (`src/main.py`).
4. **Camera list from config, not `frames/*.jpg`** (`server/app.py` `list_cameras()`), and a snapshot
   every ~60 s for metrics-only cameras so the Calibration Studio can draw zones on them.
5. **Per-camera target fps for RTSP** (today `fps_target` only throttles video files).

The tracker, analytics, storage and dashboard APIs stay unchanged.

## Test one unit before buying more (with a return window)

1. Confirm the free PCIe M.2 slot; install Ubuntu 24.04 + Docker + HailoRT; `/dev/hailo0` appears.
2. `hailortcli benchmark` on the YOLO26s HEF; compare with 67/147 fps.
3. After the port: `scripts/benchmark/benchmark_models.sh` on `entrance_sample`. Pass: **≥ 30 detections/s**
   and tracker recall within a few points of **76%**.
4. One-hour soak: 1 live + 3 metrics sub-streams. Each camera holds its fps, CPU < 70%, temperature stable.
5. Record the results in `../models/model-benchmark.md`.
