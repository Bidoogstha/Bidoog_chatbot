"""
ingest.py
---------
One-time script (also called at container startup in start.sh).
Reads bidoog.txt, splits it into overlapping chunks,
converts each chunk to a vector using sentence-transformers,
and stores everything in ChromaDB.

Run manually:  python ingest.py
Run at startup: called by start.sh before uvicorn starts
"""

import os
import re
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── paths ──────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE    = os.path.join(BASE_DIR, "knowledge", "bidoog.txt")
CHROMA_PATH  = os.path.join(BASE_DIR, "chroma_db")
COLLECTION   = "bidoog_knowledge"

# ── chunking config ─────────────────────────────────────
CHUNK_SIZE   = 400   # words per chunk
CHUNK_OVERLAP = 60   # words of overlap between chunks


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """
    Split text into overlapping word-level chunks.
    Overlap means the last `overlap` words of chunk N
    become the first `overlap` words of chunk N+1.
    This stops important context from being cut in half.
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += size - overlap
    return chunks


def ingest():
    print("📄  Loading knowledge base...")
    text = load_text(KNOWLEDGE)

    print("✂️   Chunking text...")
    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"     → {len(chunks)} chunks created")

    print("🧠  Loading embedding model (all-MiniLM-L6-v2)...")
    # This model is 80MB, CPU-only, fast enough for a portfolio chatbot.
    # We load it once here at ingest time — not on every request.
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("🔢  Generating embeddings...")
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()

    print("💾  Storing in ChromaDB...")
    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False)
    )

    # Delete existing collection so re-ingestion is always clean
    try:
        client.delete_collection(COLLECTION)
        print("     → Deleted old collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"}   # cosine similarity for semantic search
    )

    # ChromaDB expects lists of strings for ids
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=[{"chunk_index": i} for i in range(len(chunks))]
    )

    print(f"✅  Ingestion complete — {len(chunks)} chunks stored in ChromaDB")
    return len(chunks)


if __name__ == "__main__":
    ingest()
