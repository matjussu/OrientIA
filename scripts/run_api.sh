#!/usr/bin/env bash
# Lance le wrapper FastAPI OrientIA en local pour smoke E2E.
#
# Usage : ./scripts/run_api.sh [PORT]
# Defaults : PORT=8000, single worker (état mutable `_pipeline.last_validation`).
#
# Auth : si ORIENTIA_API_KEY est set dans .env, Bearer auth est activée.
# Sinon, auth désactivée (dev local sans token).

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "ERREUR : .venv introuvable. Lance d'abord : python3 -m venv .venv && pip install -r requirements.lock" >&2
    exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# Charge .env si présent (export des vars MISTRAL_API_KEY, ORIENTIA_API_KEY, etc.)
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

PORT="${1:-${PORT:-8000}}"

if [ -n "${ORIENTIA_API_KEY:-}" ]; then
    AUTH_STATE="enabled"
else
    AUTH_STATE="disabled (no ORIENTIA_API_KEY in env)"
fi

echo "Starting OrientIA API on port $PORT — Bearer auth $AUTH_STATE"
exec uvicorn src.api.server:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 1 \
    --reload
