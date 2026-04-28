#!/bin/bash
# scripts/launch_qa_gen_nuit.sh — Sprint 9-data Ordre 2/2
#
# Lance la génération 1000 Q&A en tmux session detachable (background).
# Surveillance Jarvis : `tmux attach -t qa-gen` pour reattach.
#
# Usage :
#   bash scripts/launch_qa_gen_nuit.sh                # défauts (parallel=3, target=1020)
#   bash scripts/launch_qa_gen_nuit.sh 5 1020         # parallel=5 (Max 20x), target=1020
#   bash scripts/launch_qa_gen_nuit.sh 2 500          # parallel=2 (Max 5x), target=500 (fallback)
#
# Variables d'environnement (override CLI possibles) :
#   QA_PARALLEL=3        # sub-agents simultanés
#   QA_TARGET=1020       # cap nb total Q&A
#   QA_MODEL=claude-opus-4-7  # model flag (vide = default session)
#   QA_RATE_DELAY=0.5    # délai entre calls subprocess
#   QA_MAX_RETRIES=3     # retries sur 429
#
# Logs : logs/golden_qa_gen_v1_YYYYMMDD_HHMMSS.log
# Output : data/golden_qa/golden_qa_v1.jsonl (append-only, resumable)
#
# Stop : `tmux send-keys -t qa-gen C-c` (graceful shutdown via SIGINT handler)
#   ou `tmux kill-session -t qa-gen` (hard kill — ne pas faire en prod)

set -euo pipefail

# CD sur le repo OrientIA (resolve relatif au script)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

# Args / env
QA_PARALLEL="${1:-${QA_PARALLEL:-3}}"
QA_TARGET="${2:-${QA_TARGET:-1020}}"
QA_MODEL="${QA_MODEL:-claude-opus-4-7}"
QA_RATE_DELAY="${QA_RATE_DELAY:-0.5}"
QA_MAX_RETRIES="${QA_MAX_RETRIES:-3}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="logs/golden_qa_gen_v1_${TIMESTAMP}.log"
OUTPUT_JSONL="data/golden_qa/golden_qa_v1.jsonl"
CONFIG_YAML="config/diverse_prompts_50.yaml"

mkdir -p logs data/golden_qa

# Sanity checks pré-launch
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux non installé — apt install tmux" >&2
    exit 1
fi

if [[ ! -f "$CONFIG_YAML" ]]; then
    echo "❌ Config YAML absente : $CONFIG_YAML" >&2
    exit 1
fi

if [[ ! -d ".venv" ]]; then
    echo "❌ .venv absent — créer avec python -m venv .venv && pip install -r requirements.lock" >&2
    exit 1
fi

# Tuer la session qa-gen existante si présente (avec confirm)
if tmux has-session -t qa-gen 2>/dev/null; then
    echo "⚠️  Session tmux 'qa-gen' déjà active. Kill ? [y/N]"
    read -r REPLY
    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        tmux kill-session -t qa-gen
    else
        echo "Aborted (lance avec un autre nom de session ou kill manuellement)."
        exit 1
    fi
fi

# Construit la commande python
MODEL_FLAG=""
if [[ -n "$QA_MODEL" ]]; then
    MODEL_FLAG="--model $QA_MODEL"
fi

CMD="cd '$REPO_DIR' && \
source .venv/bin/activate && \
python scripts/generate_golden_qa_v1.py \
    --config $CONFIG_YAML \
    --output $OUTPUT_JSONL \
    --parallel $QA_PARALLEL \
    --target $QA_TARGET \
    --rate-limit-delay $QA_RATE_DELAY \
    --max-retries $QA_MAX_RETRIES \
    $MODEL_FLAG \
    2>&1 | tee $LOG_FILE; \
echo '==> EXIT $?' | tee -a $LOG_FILE"

echo "==> Lancement tmux session 'qa-gen'"
echo "    parallel: $QA_PARALLEL, target: $QA_TARGET, model: ${QA_MODEL:-default}"
echo "    rate_limit_delay: ${QA_RATE_DELAY}s, max_retries: $QA_MAX_RETRIES"
echo "    log: $LOG_FILE"
echo "    output: $OUTPUT_JSONL"
echo

tmux new-session -d -s qa-gen "$CMD"

echo "✅ Session 'qa-gen' lancée en background."
echo
echo "Commands utiles :"
echo "  tmux attach -t qa-gen        # reattach pour observer"
echo "  tmux send-keys -t qa-gen C-c # graceful shutdown (SIGINT)"
echo "  tmux kill-session -t qa-gen  # hard kill (à éviter)"
echo "  tail -f $LOG_FILE            # tail logs en background"
echo "  wc -l $OUTPUT_JSONL          # progression Q&A produites"
echo
echo "Surveillance Jarvis :"
echo "  - Check 01h : qualité 30-50 premiers Q&A"
echo "  - Check 04h : stats keep/flag/drop + rythme"
echo "  - Stop conditions : drop >30% / rate limit / divergence"
echo "  - Report matin 7h"
