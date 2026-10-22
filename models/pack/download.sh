#!/usr/bin/env bash
# Thin wrapper — verified pack downloader lives in scripts/download_pack_models.py
# (sha256 / LFS-safe / core pack only; no --include-research by default).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/scripts/download_pack_models.py" --dest "$ROOT/models/pack" "$@"
