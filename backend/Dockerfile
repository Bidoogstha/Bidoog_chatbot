# ══════════════════════════════════════════════════════════════
# Dockerfile — BIDOOG CHATBOT BACKEND
#
# Build target: Railway (4GB image limit)
# Wall 1 fix: CPU-only PyTorch declared in requirements.txt
#             keeps image under 2GB total.
# ══════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── system deps ────────────────────────────────────────────────
# build-essential is needed for some chromadb native dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── python deps ────────────────────────────────────────────────
# Copy requirements first so Docker layer cache works:
# if requirements.txt hasn't changed, this layer is cached
# and rebuilds are fast.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── pre-download the embedding model ──────────────────────────
# Download all-MiniLM-L6-v2 at BUILD time, not at runtime.
# This means the model is baked into the image — no cold-start
# download delay on first request.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── app code ───────────────────────────────────────────────────
COPY . .

# ── start script permissions (Wall 4 fix) ─────────────────────
# start.sh MUST be executable. If you re-clone this repo and
# git doesn't preserve the executable bit, the container
# fails with "Permission denied" on start.
# Fix: chmod in Dockerfile so it's always set at build time.
RUN chmod +x start.sh

# Railway sets PORT env var automatically
EXPOSE 8000

CMD ["./start.sh"]
