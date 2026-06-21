#!/bin/bash
# ══════════════════════════════════════════════════════════════
# start.sh — CONTAINER STARTUP SCRIPT
#
# Wall 2 fix: Railway filesystem is ephemeral.
# ChromaDB stored on disk gets wiped on every redeploy.
# Solution: re-run ingest.py at startup so the knowledge base
# is always fresh before the server starts accepting requests.
#
# Wall 4 fix: this file must have executable permission.
# It's set in Dockerfile with chmod +x.
# If you EVER see "Permission denied" on Railway:
#   git update-index --chmod=+x start.sh
#   git commit -m "fix: restore executable bit on start.sh"
# ══════════════════════════════════════════════════════════════

set -e   # exit immediately if any command fails

echo "═══════════════════════════════════════"
echo "  BIDOOG CHATBOT — STARTUP"
echo "═══════════════════════════════════════"

echo ""
echo "→ Step 1: Ingesting knowledge base into ChromaDB..."
python ingest.py

echo ""
echo "→ Step 2: Starting FastAPI server..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --log-level info
