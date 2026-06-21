"""
rag.py
------
Core RAG logic:
  1. Load ChromaDB collection and embedding model (once, at startup)
  2. Given a user question, find the 4 most relevant chunks
  3. Build a prompt: context chunks + question → send to Gemini
  4. Stream the response back

Nothing in this file touches HTTP — that's main.py's job.
"""

import os
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── paths ───────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION  = "bidoog_knowledge"

# ── constants ───────────────────────────────────────────
TOP_K            = 4     # how many chunks to retrieve per query
MAX_OUTPUT_TOKENS = 512  # keep responses concise

# ── system prompt ───────────────────────────────────────
# This defines Bidoog's chatbot persona.
# It tells Gemini what it is, what it knows, and how to behave.
SYSTEM_PROMPT = """You are Bidoog's personal AI assistant, embedded in his portfolio website.

Your job is to answer questions from recruiters, professors, collaborators, and anyone curious about Bidoog Shrestha — his background, projects, skills, experience, and availability.

Personality:
- Warm, direct, and confident — like Bidoog himself
- Technical when the question is technical, human when the question is personal
- Never robotic. Never a list of bullet points unless it genuinely helps
- Honest: if you don't know something, say so simply

Rules:
1. Answer ONLY using the context provided below. Do not make up facts, dates, or details.
2. If a question is completely outside the provided context, say: "I don't have that info, but you can reach Bidoog directly at bshrestha@knox.edu"
3. Keep answers concise — 2 to 4 sentences for most questions, longer only for technical deep-dives
4. When asked about projects, lead with what the project DOES and why it matters, not the tech stack
5. Never say "according to the context" or "based on the provided information" — just answer naturally
6. If someone asks if Bidoog is available for internships, always say yes — he is actively looking

You represent Bidoog. Make a good impression."""

# ── module-level singletons (loaded once at startup) ────
_model      = None   # SentenceTransformer
_collection = None   # ChromaDB collection
_gemini     = None   # Gemini GenerativeModel


def _load_resources():
    """
    Called once at application startup (from main.py lifespan).
    Loads the embedding model and ChromaDB into memory.
    This is what prevents the 15-second cold response times —
    we pay the cost once at startup, not on every request.
    """
    global _model, _collection, _gemini

    print("🧠  Loading sentence-transformers model...")
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    print("     → Embedding model ready")

    print("📦  Connecting to ChromaDB...")
    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    _collection = client.get_collection(COLLECTION)
    print(f"     → Collection loaded ({_collection.count()} chunks)")

    print("✨  Configuring Gemini...")
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    _gemini = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.GenerationConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.4,    # low = factual and consistent
            top_p=0.9,
        ),
        system_instruction=SYSTEM_PROMPT
    )
    print("     → Gemini ready")


def retrieve(question: str) -> list[str]:
    """
    Embed the question and find the TOP_K most similar chunks
    in ChromaDB using cosine similarity.
    """
    embedding = _model.encode([question]).tolist()
    results   = _collection.query(
        query_embeddings=embedding,
        n_results=TOP_K,
        include=["documents"]
    )
    return results["documents"][0]   # list of chunk strings


def build_prompt(question: str, chunks: list[str]) -> str:
    """
    Combine retrieved chunks + user question into a single prompt.
    The chunks give Gemini the factual ground truth.
    The question tells it what to answer.
    """
    context = "\n\n---\n\n".join(chunks)
    return f"""CONTEXT ABOUT BIDOOG:
{context}

---

QUESTION: {question}

Answer the question using only the context above."""


def ask(question: str) -> str:
    """
    Full RAG pipeline:
    retrieve → build prompt → call Gemini → return answer string.

    Called by main.py for every chat request.
    """
    if _collection is None or _model is None or _gemini is None:
        raise RuntimeError("RAG not initialized. Call _load_resources() first.")

    chunks  = retrieve(question)
    prompt  = build_prompt(question, chunks)
    response = _gemini.generate_content(prompt)
    return response.text.strip()
