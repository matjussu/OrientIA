#!/usr/bin/env bash
# Download the InserSup DEPP dataset (insertion pro des diplômés ESR).
# File is ~570 MB so gitignored. Run this script once after clone to enable
# the attach_insertion pipeline step.

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="data/raw/insersup.csv"
URL="https://www.data.gouv.fr/api/1/datasets/r/154013bd-e890-492e-8219-71dc4292c945"

if [[ -f "$OUT" ]]; then
    echo "[skip] $OUT already exists ($(du -h "$OUT" | cut -f1))"
    exit 0
fi

echo "[fetch] InserSup DEPP → $OUT (~570 MB, may take 1-3 min)"
curl -sSL --fail -o "$OUT" "$URL"
size=$(du -h "$OUT" | cut -f1)
echo "[done]  $OUT ($size)"
echo ""
echo "InserSup ready. Run 'python -m src.collect.run_merge' to regenerate"
echo "data/processed/formations.json with insertion pro data attached."
echo ""
echo "Run 'python -m scripts.insersup_audit' to audit coverage + outliers."
