# Sample Video Sources

Videos in this directory that are not synthetically generated (see
`scripts/generate_sample_video.py` for `entrance_sample.mp4` and
`checkout_sample.mp4`) are listed here with their origin and license, so
provenance stays auditable.

| File | Source | License | Notes |
|---|---|---|---|
| `mall_concourse_01.mp4` | [Pexels video 2985409](https://www.pexels.com/video/people-spending-time-inside-a-mall-2985409/) by Joshua Santos | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | Elevated/overhead concourse view, multiple pedestrians, escalators. Downscaled from source 2560x1440 to 1280x720 and re-encoded (H.264, `libx264 -crf 26`) with ffmpeg to reduce repo size; original runtime ~86s. |
| `mall_promenade_01.mp4` | [Pexels video 5799354](https://www.pexels.com/video/view-of-a-shopping-mall-5799354/) | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | High elevated angle over a multi-level mall promenade, pedestrians at a distance. Same downscale/re-encode as above; original runtime ~72s. |
| `test_footage1.mp4` | Pre-existing in repo as of this branch; origin not documented at the time it was added | Unknown — verify before using beyond internal dev/testing | Real handheld supermarket walkthrough footage (crowded aisles, eye-level, not an elevated CCTV angle). |
| `mall_entrance_topdown_01.mp4` | [Pexels video 5456688](https://www.pexels.com/video/high-angle-view-of-shopping-mall-entrance-5456688/) | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | Dramatic straight-down atrium/entrance view. Pedestrians are small in frame (far/high vantage) -- useful as a stress test for far-distance detection, not a primary tracking benchmark clip. ~40s, downscaled to 1280x720. |
| `mall_crowd_dense_01.mp4` | [Pexels video 15007111](https://www.pexels.com/video/high-angle-view-of-a-crowded-shopping-mall-15007111/) | [Pexels License](https://www.pexels.com/license/) — free for commercial use, no attribution required | High angle over a dense, busy mall concourse -- good for crowd-density/occlusion stress testing. ~31s, downscaled to 1280x720. |

## Why these two were chosen

Both are real (non-synthetic) footage with a genuinely elevated, security-camera-like
vantage point over multiple simultaneously visible pedestrians — closer to an actual
retail CCTV mount than eye-level "walking tour" style stock footage, and long enough
(1-2 minutes) to exercise sustained tracking, not just single detections. They are
**not** wired into `configs/cameras.yaml` as the active source; they're additional
candidate test inputs for tracker/detector benchmarking (see `docs/mvp-gap-analysis.md`
§8 M4), the same way `test_footage1.mp4` was left as a commented candidate rather than
switched to automatically.

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
