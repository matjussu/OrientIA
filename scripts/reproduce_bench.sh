#!/usr/bin/env bash
# Bench complet OrientIA Phase D — orchestre toutes les étapes mesurables.
#
# Usage :
#   ./scripts/reproduce_bench.sh             # full bench (~$25-30, ~2-3h)
#   ./scripts/reproduce_bench.sh --dry-run   # valide l'env + workflow sans dépenser
#   ./scripts/reproduce_bench.sh --skip-judges  # pas de Claude+GPT-4o judges (~$15 économisés)
#   ./scripts/reproduce_bench.sh --skip-factcheck  # pas de Haiku factcheck (~$3-5 économisés)
#
# Pré-requis :
#   - .venv activable
#   - .env présent avec MISTRAL_API_KEY + ANTHROPIC_API_KEY + OPENAI_API_KEY
#   - data/processed/formations.json (alias actif vers v7) + data/embeddings/formations.index
#   - data/golden_eval/golden_60.json
#   - tests/mini_bench/questions_20.json
#
# Output : results/bench_v7_v4_1_<TIMESTAMP>/ avec :
#   - audit_v7.md, mini_bench.json, spot_check.txt
#   - eval_recall_v7.json
#   - generation/responses_blind.json, label_mapping.json
#   - judges/scores_claude.json, scores_gpt4o.json
#   - factcheck/scores_haiku.json
#   - SUMMARY.md (verdict GO/NO-GO via synthesize_bench_results.py)

set -euo pipefail

cd "$(dirname "$0")/.."

DRY_RUN=0
SKIP_JUDGES=0
SKIP_FACTCHECK=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --skip-judges) SKIP_JUDGES=1 ;;
        --skip-factcheck) SKIP_FACTCHECK=1 ;;
        *) echo "Unknown arg: $arg" >&2; exit 1 ;;
    esac
done

TIMESTAMP=$(date -u +"%Y-%m-%d_%H%M%S")
OUT_DIR="results/bench_v7_v4_1_${TIMESTAMP}"
mkdir -p "$OUT_DIR"/{generation,judges,factcheck}

echo "=== reproduce_bench.sh ==="
echo "Output : $OUT_DIR"
echo "Dry-run : $DRY_RUN"
echo "Skip judges : $SKIP_JUDGES"
echo "Skip factcheck : $SKIP_FACTCHECK"
echo ""

# --- Pre-flight checks ---
echo "[0/8] Pre-flight checks..."

if [ ! -d ".venv" ]; then
    echo "ERROR: .venv missing. Run: python3 -m venv .venv && pip install -r requirements.lock" >&2
    exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

for var in MISTRAL_API_KEY ANTHROPIC_API_KEY OPENAI_API_KEY; do
    if [ -z "${!var:-}" ]; then
        if [ "$var" = "MISTRAL_API_KEY" ]; then
            echo "ERROR: $var missing (required)" >&2
            exit 1
        elif [ "$SKIP_JUDGES" = "0" ] && [ "$var" = "ANTHROPIC_API_KEY" ]; then
            echo "ERROR: $var missing (required for judges, use --skip-judges to bypass)" >&2
            exit 1
        elif [ "$SKIP_JUDGES" = "0" ] && [ "$var" = "OPENAI_API_KEY" ]; then
            echo "ERROR: $var missing (required for judges, use --skip-judges to bypass)" >&2
            exit 1
        elif [ "$SKIP_FACTCHECK" = "0" ] && [ "$var" = "ANTHROPIC_API_KEY" ]; then
            echo "ERROR: $var missing (required for factcheck, use --skip-factcheck to bypass)" >&2
            exit 1
        else
            echo "WARN: $var missing (skip mode active, OK)"
        fi
    else
        echo "  $var: set"
    fi
done

for f in data/processed/formations.json data/embeddings/formations.index data/golden_eval/golden_60.json tests/mini_bench/questions_20.json; do
    if [ ! -f "$f" ]; then
        echo "ERROR: $f missing" >&2
        exit 1
    fi
    echo "  $f: present ($(du -h "$f" | cut -f1))"
done

if [ "$DRY_RUN" = "1" ]; then
    echo ""
    echo "DRY-RUN OK. Workflow validated, env complete. Quitting before any API call."
    rmdir "$OUT_DIR"/{generation,judges,factcheck} "$OUT_DIR" 2>/dev/null || true
    exit 0
fi

# --- 1. Audit data baseline ---
echo ""
echo "[1/8] Audit Phase 0 v7 corpus..."
python scripts/audit_phase_0_v5.py \
    --corpus "$(pwd)/data/processed/formations.json" \
    --output "$OUT_DIR/audit_v7.md"

# --- 2. Mini-bench (gratuit Mistral seulement) ---
echo ""
echo "[2/8] Mini-bench v4.1 strict_v4 (23q internes)..."
python scripts/mini_bench.py --phase strict_v4 --out "$OUT_DIR/mini_bench.json"

# --- 3. Spot-check 13q (~$0.10) ---
echo ""
echo "[3/8] Spot-check v5 (13q domains dormants)..."
python scripts/spot_check_v5.py 2>&1 | tee "$OUT_DIR/spot_check.txt"

# --- 4. Eval recall sur golden_60 (~$0.40) ---
echo ""
echo "[4/8] Eval recall@k + nDCG + refusal sur golden_60..."
python scripts/eval_recall.py \
    --golden data/golden_eval/golden_60.json \
    --out "$OUT_DIR/eval_recall_v7.json"

# --- 5. Generation 7-system × 60q (~$3-4) ---
echo ""
echo "[5/8] Generation 7-system × 60q (run_real_full)..."
python -m src.eval.run_real_full \
    --questions data/golden_eval/golden_60.json \
    --out-dir "$OUT_DIR/generation"

# --- 6. Multi-judge Claude + GPT-4o ($15-20) ---
if [ "$SKIP_JUDGES" = "0" ]; then
    echo ""
    echo "[6/8] Multi-judge Claude + GPT-4o sur 420 réponses..."
    python -m src.eval.run_judge_multi \
        --responses "$OUT_DIR/generation/responses_blind.json" \
        --out-dir "$OUT_DIR/judges" \
        --judges claude,gpt4o
else
    echo "[6/8] SKIPPED (--skip-judges)"
fi

# --- 7. Haiku factcheck ($3-5) ---
if [ "$SKIP_FACTCHECK" = "0" ]; then
    echo ""
    echo "[7/8] Haiku factcheck claims sur 420 réponses..."
    python -m src.eval.run_haiku_factcheck \
        --responses "$OUT_DIR/generation/responses_blind.json" \
        --out "$OUT_DIR/factcheck/scores_haiku.json"
else
    echo "[7/8] SKIPPED (--skip-factcheck)"
fi

# --- 8. Synthesis SUMMARY.md ---
echo ""
echo "[8/8] Synthesis verdict GO/NO-GO..."
python scripts/synthesize_bench_results.py \
    --bench-dir "$OUT_DIR" \
    --out "$OUT_DIR/SUMMARY.md"

echo ""
echo "=== bench complet ==="
echo "Output : $OUT_DIR"
echo "Verdict : $(grep -m1 'Verdict global' "$OUT_DIR/SUMMARY.md" || echo 'check SUMMARY.md')"
