# Dataset curation — initial evaluation-only set

## Outcome

The source evaluation checkout had **2 extracted frames from 2 Pexels clips**, paired with approximate point-in-time counts. This review branch carries the text-only count records and provenance notes; it excludes the video and frame files. The notes support neither training nor detection precision/recall or tracking identity metrics.

## Included

- `mall_entrance_topdown_01.mp4`, frame 500: expected count 9. The original note excludes distant/ambiguous figures, so this count may be low.
- `mall_promenade_01.mp4`, frame 900: expected count 4. The original note excludes ambiguous figures reflected in glass.

The source notes document the two Pexels references in `data/sample_videos/SOURCES.md`; verify the specific source and license before reuse. The extracted JPEGs and source videos are not present in this review tree. Do not treat a path in a manifest as an included or authorized asset.

## Not scored in this set

- `entrance_sample.mp4`: its provenance/license is unknown, so it is excluded.
- Garage: ten checkpoint images exist, but every expected count is null. The preparation report also lists a `garage_part06` and 66.6 usable minutes, while the present clips total about 60 minutes and use a different split naming. These need reconciliation before use.
- Restaurant: owner-consented for internal testing, but there are no independent count or identity labels.
- The ten ID-switch clips are automatically selected candidate events, not verified switches. Their attached tracks are model predictions, not ground truth.
- `checkout_sample.mp4` is synthetic and is not representative of real footage.

## Limits and next useful annotation

The two counts are not box annotations. Detector output can be compared as a predicted count versus the recorded count, with the source uncertainty stated; TP/FP/FN, precision, recall, F1, and mAP cannot be computed. No source has frame-level person identities, so IDF1/MOTA/MOTP and true ID-switch rate are unavailable. Pose, face/demographics, and product outputs also lack corresponding labels and will not receive invented scores.

A meaningful next dataset increment needs manually reviewed person boxes across several frames per clip and, for tracking, consistent anonymous track IDs across a short sequence. Until then, this set is evaluation-only and does not justify fine-tuning.
