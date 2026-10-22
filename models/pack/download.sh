#!/usr/bin/env bash
# Download segregated pack weights into models/pack/ (idempotent).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

download() {
  local url="$1" dest="$2" min="${3:-1000000}"
  mkdir -p "$(dirname "$dest")"
  if [[ -f "$dest" ]] && [[ "$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest")" -ge "$min" ]]; then
    echo "present: $dest"
    return 0
  fi
  echo "fetch: $dest"
  curl -L --fail --retry 3 -o "${dest}.part" "$url"
  mv "${dest}.part" "$dest"
}

download \
  "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt" \
  "$ROOT/01-detection/yolo26n/yolo26n.pt" \
  4000000

download \
  "https://huggingface.co/paulosantiago/osnet_x0_25_msmt17/resolve/main/osnet_x0_25_msmt17.pt" \
  "$ROOT/03-reid/osnet-x0_25/osnet_x0_25_msmt17.pt" \
  2000000

echo "Pack download complete."
