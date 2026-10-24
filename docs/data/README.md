# Data and evaluation evidence

This folder holds the small, text-only evaluation record carried forward from the original `ml/dataset-research-train-eval` checkout. It contains approximate point-count labels and a model report, not source footage or extracted frames. It does not establish detector or tracking accuracy.

- [`MODEL_EVAL_REPORT.md`](MODEL_EVAL_REPORT.md) describes the two-checkpoint CPU spot check and its limits.
- [`ml_scores.json`](ml_scores.json) records the machine-readable results; null accuracy fields are intentional.
- [`DATASET_CURATION.md`](DATASET_CURATION.md), [`dataset_manifest.json`](dataset_manifest.json), [`point_counts.json`](point_counts.json), and [`eval_only.json`](eval_only.json) describe what the tiny set can and cannot support.
- Label and raw-footage rules are in [`labels-README.md`](labels-README.md) and [`raw-videos-README.md`](raw-videos-README.md).

The report files were copied from the preserved local checkout on 2026-10-24. Frames, videos, weights, databases, and generated outputs were not copied. Some report paths point to data that remains local to that checkout. To reproduce the benchmark, use the original approved files and documented environment; do not infer accuracy from count coverage.
