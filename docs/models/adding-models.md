# Adding or changing a model

This guide maps the code paths a contributor must update when adding a model. A
catalog row, a checkpoint on disk, an enabled switch, and a model that is running
are four different states. Only a fresh worker snapshot can support a `LIVE` claim.

## Source map

| Concern | Source of truth | What belongs there |
|---|---|---|
| Operator-facing model list, purpose, license, weights, and availability probes | `src/perception/model_stack.py` | Add a catalog entry with an honest initial state. Disk presence alone must never be described as loaded. |
| Runtime loader and model lifecycle | `src/perception/registry.py` | Add or reuse a loader kind, register a `ModelSpec`, and report load errors instead of silently pretending it is active. |
| Per-camera registration and inference cadence | `src/main.py` | Register the selected spec, honor enablement, keep expensive enrichment on its declared tier, and publish the observed state. |
| Product defaults and performance choices | `configs/pipeline.yaml` plus the specific local profile under `local-runtime/` | Set checkpoint path, model toggle, device, thresholds, and cadence. Local overrides are not automatically shared with Docker or other machines. |
| Operator on/off controls | `server/model_switches.py`, `local-runtime/model-switches.json`, and `server/app.py` | Add a switch only when it can control a real runtime path. Enforce privacy gates server-side. |
| Live state and dashboard status | `src/main.py` live snapshot writer; `server/app.py` model-stack and health APIs; `server/templates/index.html` | Status text must come from the current snapshot. Show waiting/off/error when runtime evidence is absent. |
| Accuracy or count-error claims | `scripts/benchmark/`, labeled data, `server/model_evaluation.py`, and `/api/v1/models/evaluation` | Report only measured results with model, clip, config, label-count, and evaluation-time provenance. Otherwise show “Not measured.” |
| Automated checks | `tests/` | Cover load success/failure, missing weights, switches and gates, cadence, output shape, stale snapshots, and dashboard/API state. |

The model catalog and runtime registry are intentionally separate: the catalog is
the product-facing inventory; the registry is the set of loader specifications for
one pipeline. Neither is proof that an inference completed. The live snapshot is
the evidence of actual runtime activity.

## Contribution checklist

1. Confirm the model adds a distinct capability. If it duplicates a selected model,
   document the measured reason to keep both; do not load redundant models by default.
2. Record the upstream source, exact license for code and weights, version, weight
   filename/checksum, storage location, and whether downloading is optional. Do not
   add large or unreviewed checkpoints to Git.
3. Add a catalog entry in `src/perception/model_stack.py` and a `ModelSpec` in the
   appropriate pipeline setup in `src/main.py`. Keep the task, tier, and purpose
   explicit.
4. Implement/reuse the loader in `src/perception/registry.py`. Missing optional
   weights should report unavailable; required-model failures should stop the
   pipeline rather than emit plausible zero metrics.
5. Set defaults and cadence in `configs/pipeline.yaml`; update local runtime or
   Docker overrides only when that environment should use the model. Do not treat
   a user-facing toggle as proof that weights exist or inference is running.
6. Add tests for present/missing weights, initialization failure, switch behavior,
   privacy gates, inference output format, call cadence, and status transitions.
7. Connect outputs to analytics only when the model result has the required
   calibration and semantics. A person detector is not shelf-gap truth; a pose
   point is not a person box; detector confidence is not model accuracy.
8. For accuracy claims, create a labeled evaluation report matching the schema
   enforced in `server/model_evaluation.py`. It must be no more than seven days old
   and include labeled frames and people plus model, clip, dataset, and config.
9. Update `docs/models/model-stack-policy.md` and the relevant integration or
   performance guide. Name what is LIVE, optional, gated, partial, or future.
10. Run focused tests first, then the full test suite and rendered Compose checks.
    In the handoff, list the exact changed files and state which checks used real
    weights/footage versus stubs.

## Evaluation report contract

The optional `MODEL_EVALUATION_PATH` JSON file (default:
`ml_dataset/reports/model-evaluation.json`) has this shape:

```json
{
  "schema_version": 1,
  "evaluated_at": "2026-10-24T10:00:00Z",
  "model": "YOLO26s",
  "clip": "entrance-labeled-v1.mp4",
  "config_id": "pilot-balanced-512",
  "dataset": {
    "name": "entrance labels v1",
    "labeled_frames": 120,
    "ground_truth_people": 340
  },
  "metrics": {
    "precision": 0.91,
    "recall": 0.82,
    "f1": 0.86,
    "count_mae": 0.7
  }
}
```

Precision, recall, and F1 are fractions in `[0, 1]`; `count_mae` is a non-negative
mean absolute count error. The API rejects missing, invalid, future-dated, older
than seven days, or unlabeled reports. Do not use detector confidence as a
substitute for any of these metrics.
