#!/usr/bin/env bash
# Download Parcoursup historical CSVs (2023, 2024) for Vague C trends pipeline.
# The 2025 CSV is already in data/raw/ as the baseline. Files are gitignored
# (12 MB each), so clone-reproduce requires running this script once.

set -euo pipefail

cd "$(dirname "$0")/.."

BASE_URL="https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets"

for year in 2023 2024; do
    out="data/raw/parcoursup_${year}.csv"
    if [[ -f "$out" ]]; then
        echo "[skip] $out already exists"
        continue
    fi
    dataset="fr-esr-parcoursup_${year}"
    url="${BASE_URL}/${dataset}/exports/csv?delimiter=%3B"
    echo "[fetch] $year → $out"
    curl -sSL --fail -o "$out" "$url"
    size=$(wc -c < "$out")
    echo "[done]  $out (${size} bytes)"
done

echo ""
echo "Historical CSVs ready. Run 'python -m src.collect.run_merge' to"
echo "regenerate data/processed/formations.json with trends."
