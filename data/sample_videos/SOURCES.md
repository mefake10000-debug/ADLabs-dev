# Sample Video Sources

This provenance inventory includes candidate, excluded, and local-only footage.
The video files themselves are not included in this review branch. Do not treat a
listed source as permission to copy, retain, or evaluate footage unless its status
and license are explicitly confirmed.

| File | Source | License | Notes |
|---|---|---|---|
| `mall_concourse_01.mp4` | [Pexels video 2985409](https://www.pexels.com/video/people-spending-time-inside-a-mall-2985409/) by Joshua Santos | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | Elevated/overhead concourse view, multiple pedestrians, escalators. Downscaled from source 2560x1440 to 1280x720 and re-encoded (H.264, `libx264 -crf 26`) with ffmpeg to reduce repo size; original runtime ~86s. |
| `mall_promenade_01.mp4` | [Pexels video 5799354](https://www.pexels.com/video/view-of-a-shopping-mall-5799354/) | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | High elevated angle over a multi-level mall promenade, pedestrians at a distance. Same downscale/re-encode as above; original runtime ~72s. |
| `entrance_sample.mp4` | **EXCLUDED.** Pre-existing in destination history; origin and license are unknown | **Unknown; not approved for redistribution or evaluation** | Removed from the review branch’s new tree and commits. Do not re-add until provenance, license, and consent are verified. The preserved original source checkout remains untouched. |
| `enterance_sample_recorded.mp4` | Screen recording of the dashboard's live stream while running `entrance_sample.mp4` through the Docker pipeline (2026-09-19) | Your own recording | Evidence for `docs/performance/recorded-run-analysis.md`. 55MB; intentionally **not committed**. |
| `store_entrance_near_01.mp4` | [Pexels video 6641527](https://www.pexels.com/video/people-going-inside-a-store-with-automatic-sliding-doors-6641527/) | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | Fixed camera on an outdoor grocery storefront with automatic doors; pedestrian is ~230px tall at 720p (close range, comparable to/larger than `entrance_sample.mp4`), unlike the mall clips where people are ~40-60px. Not in-store. ~20s, downscaled to 1280x720. |
| `test_footage1.mp4` | Identified 2026-09-19 as byte-identical to [Pexels video 10901926](https://www.pexels.com/video/customers-shopping-at-supermarket-10901926/) (Suika Chan) | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | Real handheld supermarket walkthrough footage (crowded aisles, eye-level, not an elevated CCTV angle). |
| `mall_entrance_topdown_01.mp4` | [Pexels video 5456688](https://www.pexels.com/video/high-angle-view-of-shopping-mall-entrance-5456688/) | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | Dramatic straight-down atrium/entrance view. Pedestrians are small in frame (far/high vantage) -- useful as a stress test for far-distance detection, not a primary tracking benchmark clip. ~40s, downscaled to 1280x720. |
| `mall_crowd_dense_01.mp4` | [Pexels video 15007111](https://www.pexels.com/video/high-angle-view-of-a-crowded-shopping-mall-15007111/) | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | High angle over a dense, busy mall concourse -- good for crowd-density/occlusion stress testing. ~31s, downscaled to 1280x720. |
| `garage/` (`garage_part00`–`06`, `part04` split in two) | **Not in git: download from the team's shared drive.** Hour-long CCTV export from a garage, obtained privately with the owner's consent (2026-10-13). Prepared with `scripts/dev-tools/prepare_footage.py`; `contact_sheet.jpg` and `prep_report.json` describe it | Owner's consent; internal testing only, never commit or share outside the team | Mixed distances; people far from the camera get size-rejected at 720p. The last 1–2 minutes are a different camera. See `docs/tools/footage-tools.md`. |
| `restaurant_ch17/` (3 clips, 1.5–3 min) | **Not in git: download from the team's shared drive.** CP Plus NVR export (`.cpv`) from a restaurant bar counter, "Channel17", obtained privately with the owner's consent (2026-10-19). Converted to 720p H.264 | Owner's consent; internal testing only, never commit or share outside the team | Staff work behind the counter: test footage for telling staff from customers (`docs/product/staff-identification.md`). Clips are not continuous. |

## Candidate footage notes

Licensed Pexels clips listed above were considered candidate inputs, but are not
included in this branch. Any future use should verify the specific source license
and review the intended evaluation purpose. These unlabelled clips can support
decoder and qualitative plumbing checks, not accuracy scoring.

## Decision: Oxford Town Centre dataset -- not used

The Oxford Town Centre pedestrian-tracking dataset was considered as a
candidate for M4 benchmarking (real CCTV footage with natural occlusion).
It was **not used**: its own maintainers took the official page down in June
2020 specifically because pedestrians were filmed without consent, and it's
documented by [exposing.ai](https://exposing.ai/oxford_town_centre/) as a
cautionary surveillance-ethics case study (the footage propagated into 60+
research projects, including uses -- e.g. automated sex classification --
the filmed individuals never agreed to). Given EdgeSight's privacy-first
positioning, Mihir decided to skip it (2026-09-18)
rather than use it even as a dev-only asset. If occlusion-heavy benchmark
footage is needed later, the options are: real pilot-store CCTV footage
(once available) or a dataset with documented consent/synthetic origin --
not this one.

## Licensing caveat

Genuinely open-licensed (CC0/permissive), continuous, single-take CCTV-style footage
in the 1-5 minute range is scarce — most free stock libraries cut clips to 10-40s, and
the well-known academic pedestrian-tracking datasets (Oxford Town Centre, PETS2009,
MOT challenge sequences, etc.) are licensed for research/non-commercial use only, which
doesn't fit a commercial product's repo. These two Pexels clips were chosen because
their license is unambiguous and commercial-safe; if longer or more occlusion-heavy
footage is needed later, that likely means either filming/licensing real pilot-store
CCTV footage directly, or explicitly accepting a research-only dataset as a
dev-only/never-shipped asset (a decision for Mihir, not one made silently here).
