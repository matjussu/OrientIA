#!/usr/bin/env bash
# Archive a finished benchmark run under results/<run_name>/
# Usage: bash experiments/phase0_baseline/archive_run.sh run7_phase1_densification
set -euo pipefail
RUN_NAME="${1:?usage: archive_run.sh <run_name>}"
DEST="results/${RUN_NAME}"

if [ -e "$DEST" ]; then
  echo "Refusing to overwrite existing $DEST" >&2
  exit 1
fi

mkdir -p "$DEST/raw_responses" "$DEST/scores"
cp results/raw_responses/responses_blind.json "$DEST/raw_responses/"
cp results/raw_responses/label_mapping.json    "$DEST/raw_responses/"
cp results/raw_responses/seed.txt              "$DEST/raw_responses/"
cp results/scores/blind_scores.json           "$DEST/scores/"
cp results/scores/summary.json                 "$DEST/scores/"
cp results/scores/unblinded.json               "$DEST/scores/"

if [ -f results/scores/blind_scores_v2.json ]; then
  cp results/scores/blind_scores_v2.json        "$DEST/scores/"
  cp results/scores/summary_v2.json             "$DEST/scores/"
  cp results/scores/unblinded_v2.json           "$DEST/scores/"
fi

if [ -f results/raw_responses/retrieved_by_qid.json ]; then
  cp results/raw_responses/retrieved_by_qid.json "$DEST/raw_responses/"
fi

mkdir -p "$DEST/charts"
cp results/charts/*.png "$DEST/charts/" 2>/dev/null || true

echo "Archived to $DEST"
ls -la "$DEST/scores/"
