# Working with new CCTV footage: prepare it, then check detection on it

Two tools for every new batch of footage (e.g. from a pilot store):

1. **`scripts/prepare_footage.py`** turns a raw recorder export into clean clips the pipeline can use.
2. **`scripts/make_count_sheet.py`** + **`scripts/benchmark_tracking.py`** check *"do the people the
   tracker sees match what a person sees?"* and give a number for it.

Everything runs inside the edge container, which has ffmpeg, OpenCV and YOLO. Prepared clips in
`data/sample_videos/<name>/` are committed so the whole team can test on them (the repo is private;
the footage shows real, identifiable people, so keep it that way). GitHub rejects files over 100 MB:
use `--clip-minutes 5` for high-bitrate footage. Count sheets and working files stay local and gitignored.

## Before you start

- Stop the live analyzer while these run; they compete for the same CPU:
  `docker compose stop edge-analyzer`. Restart it afterwards with `docker compose start edge-analyzer`.
- Make sure you're allowed to use the footage (e.g. the store owner's OK), and keep it out of
  chats and shared drives.

## 1. Prepare footage

Recorder exports often arrive damaged in ways a normal video player hides:

- **Corrupted stretches.** VLC pauses, and plays on if you skip ahead. A plain conversion instead
  carries the corruption forward, so everything afterwards comes out grey, rotated or slanted.
- **Scrambled internal timestamps.** Times jump hours back and forth, which makes conversions
  duplicate or drop frames and inflates the file's apparent length.
- **H.265.** It's handled worse than H.264 by some tools and boards.

The script copies the raw video data out (which discards the broken timestamps) and cuts it into
~60-second pieces at clean frames. It then decodes **each piece with a fresh decoder**, so a
corrupted stretch spoils at most its own piece. Finally it re-encodes to H.264 720p, checks every
piece for grey or garbled frames, and slices the result into 10-minute clips.

**Run it:** put the export in any folder and mount that folder as `/raw`. Choose a short name for
the source; the clips land in `data/sample_videos/<name>/`.

```
docker compose run --rm --no-deps ^
    -v "C:/Users/Acer/Downloads:/raw:ro" ^
    -v "./data/sample_videos/garage:/out" ^
    edge-analyzer python scripts/prepare_footage.py /raw/D01_20261013091838.mp4 --name garage --out-dir /out
```

(`^` continues a line in Windows `cmd`; use `` ` `` in PowerShell, or put it all on one line.)

Useful options: `--clip-minutes 5` for shorter clips; `--drop-bad` to leave out pieces that are
mostly grey or garbled; `--piece-seconds 30` to limit how much a corrupted stretch can spoil.
Expect roughly real-time speed on our dev laptop: an hour of footage takes about an hour.

**Output, in `data/sample_videos/<name>/`:**

| File | What to do with it |
|---|---|
| `<name>_part00.mp4`, `_part01.mp4`, ... | The clips. They appear in the dashboard's Camera Setup → Video source picker. |
| `contact_sheet.jpg` | **Look at this first.** One frame per minute, one row per clip. Any grey, rotated or slanted tile is a problem. |
| `prep_report.json` | The source format, how many timestamps were broken, how much real footage there was, and every piece with grey/garbled frames — with the clip and time to look at. |

The console also lists the flagged pieces. A few flagged pieces are normal for a damaged export;
check them in the clips, and re-run with `--drop-bad` if they're mostly garbage.

**Example — the garage export (2026-10-13), 1080p H.265 claiming 73 minutes:**
- **Broken timestamps:** 220 went backwards and 180 jumped forward. They were ignored and the
  frames renumbered.
- **Result:** 71 one-minute pieces became 7 clips with **66.6 minutes of real footage**. A manual
  conversion the day before had produced only 45.5 minutes, silently losing a third of the recording
  to the broken timestamps. The burned-in clock confirms the clips run continuously from 09:18 to
  about 10:28.
- **The damaged stretch where VLC froze (11:17)** was flagged "bad", automatically. One piece was
  unreadable and dropped. 24 others had a few grey frames each.
- **What it can't catch:** the last minute or two of the export shows a *different* camera, with
  its clock reading the day before. The script has no way to tell, so always look at the end of the
  contact sheet, and use the burned-in clock to confirm continuity.

## 2. Check detection on a clip

**Step 1: make the count sheet.** This picks 10 evenly spaced frames, skipping damaged ones:

```
docker compose run --rm --no-deps edge-analyzer python scripts/make_count_sheet.py data/sample_videos/garage/garage_part00.mp4
```

This writes, to `data/storage/count_checks/garage_part00/`:
- one image per checkpoint (`checkpoint_01_f000600.jpg`, ...);
- `sheet.jpg`, with all of them at a glance;
- `ground_truth.json`.

**Step 2: count.** Open each checkpoint image and count the people in it, using the rule in the file
(it matches the rule used for `entrance_sample`):
- **Count:** everyone whose head or upper body is clearly visible, including staff, people partly
  hidden or cut off by the edge, and children.
- **Don't count:** a lone hand or a pair of feet.

Type each number into that checkpoint's `"expected_visible_people"` in `ground_truth.json`, and fill
in `"notes"` with who counted and anything ambiguous. Leaving a checkpoint `null` just skips it, so
you can score after counting only some of them. Budget about a minute per checkpoint.

**Step 3: score it.** This runs the real detector + tracker at the live rate (8 fps) and compares at
each checkpoint:

```
docker compose run --rm --no-deps edge-analyzer python scripts/benchmark_tracking.py ^
    data/sample_videos/garage/garage_part00.mp4 ^
    --ground-truth data/storage/count_checks/garage_part00/ground_truth.json ^
    --process-fps 8 --save-checkpoints data/storage/count_checks/garage_part00/scored
```

It takes about as long as the clip (≈10 min for a 10-minute clip on our laptop). You get:

- **A table per checkpoint:** your count, raw detections, people the tracker reports, and the
  percentage found.
- **"Where people are lost":** whether missed people were never detected, too small, or the wrong
  shape (e.g. lying down or bent over).
- **The headline number, mean tracker-output recall:** the share of people the dashboard would
  count. Compare it with `entrance_sample`'s **76%** (`docs/model-benchmark.md`).
- **`scored/checkpoint_f*.jpg`:** each checkpoint frame with **green** boxes for tracked people
  (what the dashboard counts) and thin **yellow** boxes for detected-but-not-tracked. Anyone without
  a box was missed. This is the fastest way to see *why* the number is what it is.

Keep counts you want to reuse by copying `ground_truth.json` into `scripts/benchmark_ground_truth/<clip>.json`.
Those are just numbers, so they're fine to commit. Then `scripts/benchmark_models.sh` can compare
models on that clip too.

## Reading the results

- **About 70–80%:** in line with `entrance_sample`. Detection works on this camera.
- **Much lower:** look at the `scored/` images. Common causes:
  - **People far from the camera** are too small. Use the camera's higher-resolution stream, or
    lower the size filters in `configs/pipeline.yaml` (`perception.min_height`, `min_area`).
    The "where people are lost" table shows these as **size-rejected**: YOLO found them and our
    filter threw them away. The filters are in **pixels**, so the same person is more likely to be
    rejected in 720p than in 1080p, and more again in a 640×360 sub-stream. On the garage camera, a
    person standing by the van at the back is size-rejected in every checkpoint at 720p.
  - **Odd poses** (crouching, bending under a car bonnet) are rejected by the shape filter
    (`max_aspect_ratio` / `min_aspect_ratio`).
  - **Glare or darkness.**
- **Counts of 0–2 people per frame** give noisy percentages: one miss is 50%. Prefer busier
  moments, or count more checkpoints (`--checkpoints 20`).
