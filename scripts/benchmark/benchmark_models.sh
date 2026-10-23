#!/bin/sh
# Speed vs accuracy for each YOLO model on THIS machine, against entrance_sample's hand counts.
# Use it to compare models, and to qualify candidate pilot hardware before buying it
# (docs/pilot-hardware.md). Run inside the edge container:
#
#   docker compose stop edge-analyzer        # don't share the CPU with the live analyzer
#   docker compose run --rm --no-deps edge-analyzer sh scripts/benchmark/benchmark_models.sh [n s m]
#   docker compose start edge-analyzer
#
# A model given as e.g. "s_openvino_model" runs models/yolo26s_openvino_model (export it first).
# Results: data/storage/model_bench/ (gitignored), plus a summary table at the end.
set -u
V=data/sample_videos/entrance_sample.mp4
GT=scripts/benchmark/benchmark_ground_truth/entrance_sample.json
OUT=data/storage/model_bench
MODELS=${*:-n s m}
mkdir -p $OUT

for M in $MODELS; do
  W=models/yolo26$M; case $M in *_model) ;; *) W=$W.pt ;; esac
  echo "=== yolo26$M: accuracy (every frame) ==="
  python scripts/benchmark/benchmark_tracking.py $V --ground-truth $GT --model $W > $OUT/accuracy_$M.log 2>&1
  echo "=== yolo26$M: speed + suspected ID switches (every frame) ==="
  python scripts/benchmark/detect_id_switches.py $V --no-clips --model $W --out-dir $OUT/switches_${M}_allframes \
    > $OUT/switches_${M}_allframes.log 2>&1
  FPS=$(python -c "import json;s=json.load(open('$OUT/switches_${M}_allframes/summary.json'));print(round(s['frames_processed']/s['wall_clock_seconds'],2))")
  echo "=== yolo26$M: suspected ID switches at the rate it sustains here ($FPS fps) ==="
  python scripts/benchmark/detect_id_switches.py $V --no-clips --model $W --process-fps $FPS --out-dir $OUT/switches_${M}_live \
    > $OUT/switches_${M}_live.log 2>&1
done

echo
echo "model              | fps here | tracker recall | switches (every frame) | switches (at fps here)"
for M in $MODELS; do
  python - "$OUT" "$M" << 'EOF'
import json, re, sys
out, m = sys.argv[1], sys.argv[2]
acc = open(f"{out}/accuracy_{m}.log").read()
recall = re.search(r"tracker-output recall: (\d+)%", acc)
every = json.load(open(f"{out}/switches_{m}_allframes/summary.json"))
live = json.load(open(f"{out}/switches_{m}_live/summary.json"))
fps = every["frames_processed"] / every["wall_clock_seconds"]
print(f"yolo26{m:<14} | {fps:8.1f} | {recall.group(1) + '%' if recall else '?':>14} | "
      f"{every['suspected_switches']:>22} | {live['suspected_switches']:>22}")
EOF
done
