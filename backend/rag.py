import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from groq import Groq

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION  = "bidoog_knowledge"
TOP_K             = 4
MAX_OUTPUT_TOKENS = 512

SYSTEM_PROMPT = """You are Bidoog's personal AI assistant embedded in his portfolio website.
Answer questions from recruiters and collaborators about Bidoog Shrestha.
Be warm, direct, and confident. Answer ONLY using the context provided.
If outside context say: I don't have that info, but reach Bidoog at bshrestha@knox.edu
Keep answers to 2-4 sentences. If asked about internship availability, always say yes."""

_model      = None
_collection = None
_groq       = None

def _load_resources():
    global _model, _collection, _groq
    print("🧠  Loading sentence-transformers model...")
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    print("     → Embedding model ready")
    print("📦  Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
    _collection = client.get_collection(COLLECTION)
    print(f"     → Collection loaded ({_collection.count()} chunks)")
    print("⚡  Configuring Groq...")
    _groq = Groq(api_key=os.environ["GROQ_API_KEY"])
    print("     → Groq ready")

def retrieve(question):
    embedding = _model.encode([question]).tolist()
    results = _collection.query(query_embeddings=embedding, n_results=TOP_K, include=["documents"])
    return results["documents"][0]

def ask(question):
    if _collection is None or _model is None or _groq is None:
        raise RuntimeError("RAG not initialized.")
    chunks  = retrieve(question)
    context = "\n\n---\n\n".join(chunks)
    prompt  = f"CONTEXT ABOUT BIDOOG:\n{context}\n\n---\n\nQUESTION: {question}\n\nAnswer using only the context above."
    response = _groq.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()