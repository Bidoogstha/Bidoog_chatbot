"""
main.py
-------
FastAPI application.

Endpoints:
  GET  /health  → Railway health check + keep-alive ping target
  POST /chat    → accepts {question: str}, returns {answer: str}

Also handles:
  - CORS (your Vercel frontend domain)
  - Custom sliding-window rate limiter (15 req/min per IP)
    — NOT SlowAPI, which has a known silent-failure bug against
      Starlette 1.0.0 (documented in README)
  - Startup warmup: ingest + model load happen before first request
"""

import os
import time
import logging
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import ingest
import rag

# ── logging ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ── rate limiter ────────────────────────────────────────
# Sliding window: max 15 requests per 60 seconds per IP.
# Gemini free tier is 15 req/min — this matches it exactly.
# We read X-Forwarded-For because Railway sits behind a proxy
# and request.client.host would always be the proxy's IP.

RATE_LIMIT_REQUESTS = 15
RATE_LIMIT_WINDOW   = 60   # seconds

_rate_store: dict[str, deque] = defaultdict(deque)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host or "unknown"


def is_rate_limited(ip: str) -> bool:
    now    = time.time()
    window = _rate_store[ip]

    # Remove timestamps older than the window
    while window and window[0] < now - RATE_LIMIT_WINDOW:
        window.popleft()

    if len(window) >= RATE_LIMIT_REQUESTS:
        return True

    window.append(now)
    return False


# ── startup / shutdown ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs at container startup — before the first request is served.
    1. Ingest bidoog.txt into ChromaDB (re-runs on every deploy
       because Railway filesystem resets — Wall 2 from README)
    2. Load embedding model + ChromaDB + Gemini into memory
       so the first real request is fast.
    """
    log.info("🚀  Starting up...")

    log.info("📄  Running ingestion pipeline...")
    n_chunks = ingest.ingest()
    log.info(f"     → {n_chunks} chunks ready")

    log.info("🧠  Warming RAG resources...")
    rag._load_resources()
    log.info("     → All resources loaded. Server is ready.")

    yield   # ← server is live here

    log.info("🛑  Shutting down.")


# ── app ─────────────────────────────────────────────────
app = FastAPI(
    title="Bidoog Chatbot API",
    description="RAG chatbot for Bidoog Shrestha's portfolio",
    version="1.0.0",
    lifespan=lifespan
)

# ── CORS ────────────────────────────────────────────────
# WALL 5 FIX: list every origin that should be allowed.
# The ALLOWED_ORIGINS env var is set in Railway dashboard.
# Format: comma-separated, e.g.:
#   https://bidoog.vercel.app,https://bidoogshrestha.com
# Always include http://localhost:5500 for local dev.

raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500"
)
origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
log.info(f"CORS origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ── request / response schemas ──────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The user's question about Bidoog"
    )


class ChatResponse(BaseModel):
    answer: str


# ── endpoints ───────────────────────────────────────────
@app.get("/health", tags=["infra"])
async def health():
    """
    Railway uses this to check the container is alive.
    Also used by the frontend keep-alive ping to prevent cold starts.
    """
    return {"status": "ok", "service": "bidoog-chatbot"}


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: Request, body: ChatRequest):
    """
    Main chat endpoint.
    Applies rate limiting, then runs the RAG pipeline.
    """
    ip = get_client_ip(request)

    if is_rate_limited(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment before asking again."
        )

    try:
        log.info(f"[{ip}] Q: {body.question[:80]}")
        answer = rag.ask(body.question)
        log.info(f"[{ip}] A: {answer[:80]}")
        return ChatResponse(answer=answer)

    except Exception as e:
        log.error(f"RAG error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong. Please try again in a moment."
        )


# ── dev entry point ─────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
