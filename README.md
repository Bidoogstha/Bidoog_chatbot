# Bidoog Shrestha — Portfolio Chatbot

A production RAG chatbot embedded in my portfolio website. Answers recruiter questions about my background, projects, and availability using Retrieval-Augmented Generation.

**Stack:** Python · FastAPI · ChromaDB · sentence-transformers · Google Gemini 1.5 Flash · Railway · Vercel

---

## How it works

```
Recruiter types a question
        ↓
FastAPI (Railway) receives it
        ↓
sentence-transformers converts the question to a vector
        ↓
ChromaDB finds the 4 most relevant chunks from bidoog.txt
        ↓
Gemini 1.5 Flash gets: context chunks + question
        ↓
Gemini answers using only real information about Bidoog
        ↓
Answer streams back to the portfolio frontend (Vercel)
```

---

## Project structure

```
bidoog-chatbot/
├── backend/
│   ├── main.py              ← FastAPI app, CORS, rate limiting, endpoints
│   ├── rag.py               ← ChromaDB retrieval + Gemini generation
│   ├── ingest.py            ← chunks bidoog.txt and stores in ChromaDB
│   ├── knowledge/
│   │   └── bidoog.txt       ← resume + LinkedIn + GitHub READMEs
│   ├── chroma_db/           ← auto-created by ingest.py (gitignored)
│   ├── requirements.txt     ← pinned versions
│   ├── Dockerfile
│   └── start.sh
└── README.md                ← you are here
```

---

## Local development

### 1. Get a free Gemini API key
Go to https://aistudio.google.com → "Get API key" → copy it.
No card required.

### 2. Clone and set up

```bash
git clone https://github.com/Bidoogstha/bidoog-chatbot.git
cd bidoog-chatbot/backend

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Set environment variable

```bash
# Mac/Linux
export GEMINI_API_KEY="your_key_here"
export ALLOWED_ORIGINS="http://localhost:5500"

# Windows PowerShell
$env:GEMINI_API_KEY="your_key_here"
$env:ALLOWED_ORIGINS="http://localhost:5500"
```

### 4. Ingest your knowledge base

```bash
python ingest.py
```

You should see: `✅  Ingestion complete — N chunks stored in ChromaDB`

### 5. Start the server

```bash
python main.py
```

Server runs at http://localhost:8000
API docs at http://localhost:8000/docs

### 6. Test it

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What projects has Bidoog built?"}'
```

---

## Deploy to Railway

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "feat: initial chatbot backend"
git remote add origin https://github.com/Bidoogstha/bidoog-chatbot.git
git push -u origin main
```

### Step 2 — Create Railway project

1. Go to railway.app → New Project → Deploy from GitHub
2. Select your `bidoog-chatbot` repo
3. Railway will detect the Dockerfile automatically

### Step 3 — Set environment variables in Railway dashboard

Go to your service → Variables tab → add:

```
GEMINI_API_KEY     = your_gemini_api_key_here
ALLOWED_ORIGINS    = https://your-portfolio.vercel.app
```

**Wall 5 note:** ALLOWED_ORIGINS must include `https://` — without it,
CORS will fail silently and you'll see "blocked by CORS policy" in
the browser network tab with no useful error message.

### Step 4 — Deploy

Railway deploys automatically on every push to main.
Check the logs tab — you should see the startup sequence:
```
→ Step 1: Ingesting knowledge base into ChromaDB...
✅  Ingestion complete
→ Step 2: Starting FastAPI server...
```

### Step 5 — Get your Railway URL

Railway gives you a public URL like:
`https://bidoog-chatbot-production.up.railway.app`

Copy this. You need it for the frontend.

---

## Add chatbot to your portfolio HTML

Paste this into your `index.html` — before `</body>`:

```html
<!-- ── CHATBOT WIDGET ── -->
<div id="chat-widget" style="
  position:fixed; bottom:28px; right:28px; z-index:1000;
  font-family:'Nunito',sans-serif;
">
  <!-- Toggle button -->
  <button id="chat-toggle" onclick="toggleChat()" style="
    width:58px; height:58px; border-radius:50%; border:none;
    background:#4EC5E8; color:white; font-size:24px;
    box-shadow:0 5px 0 #2FAFD4; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:transform .15s;
  ">💬</button>

  <!-- Chat window -->
  <div id="chat-window" style="
    display:none; position:absolute; bottom:70px; right:0;
    width:340px; height:480px;
    background:white; border-radius:20px;
    border:2px solid #F5EDD8;
    box-shadow:0 20px 60px rgba(58,39,24,.18);
    display:flex; flex-direction:column; overflow:hidden;
  ">
    <!-- Header -->
    <div style="
      background:#4EC5E8; padding:16px 18px;
      display:flex; align-items:center; gap:12px;
    ">
      <div style="
        width:38px; height:38px; border-radius:50%;
        background:rgba(255,255,255,.25);
        display:flex; align-items:center; justify-content:center;
        font-size:18px;
      ">🤖</div>
      <div>
        <div style="color:white;font-weight:800;font-size:15px">Ask about Bidoog</div>
        <div style="color:rgba(255,255,255,.8);font-size:12px;font-weight:600">Powered by Gemini · RAG</div>
      </div>
      <button onclick="toggleChat()" style="
        margin-left:auto; background:none; border:none;
        color:white; font-size:18px; cursor:pointer;
      ">✕</button>
    </div>

    <!-- Messages -->
    <div id="chat-messages" style="
      flex:1; overflow-y:auto; padding:16px;
      display:flex; flex-direction:column; gap:10px;
      background:#FDFAF3;
    ">
      <div class="msg-bot" style="
        background:white; border:2px solid #F5EDD8;
        border-radius:14px 14px 14px 4px;
        padding:10px 14px; font-size:14px; font-weight:600;
        color:#2A1F10; max-width:85%; line-height:1.5;
      ">
        Hi! 👋 I'm Bidoog's AI assistant. Ask me anything about his projects, skills, or experience.
      </div>
    </div>

    <!-- Suggestions -->
    <div id="suggestions" style="padding:8px 16px; display:flex; gap:7px; flex-wrap:wrap; background:#FDFAF3">
      <button onclick="sendSuggestion(this)" style="
        font-size:12px; font-weight:700; padding:5px 12px;
        border-radius:20px; border:2px solid #F5EDD8;
        background:white; color:#5C4230; cursor:pointer;
        transition:background .2s;
      ">MindfulCart?</button>
      <button onclick="sendSuggestion(this)" style="
        font-size:12px; font-weight:700; padding:5px 12px;
        border-radius:20px; border:2px solid #F5EDD8;
        background:white; color:#5C4230; cursor:pointer;
      ">Loan ML project?</button>
      <button onclick="sendSuggestion(this)" style="
        font-size:12px; font-weight:700; padding:5px 12px;
        border-radius:20px; border:2px solid #F5EDD8;
        background:white; color:#5C4230; cursor:pointer;
      ">Available for internship?</button>
    </div>

    <!-- Input -->
    <div style="padding:12px 16px; background:white; border-top:2px solid #F5EDD8; display:flex; gap:8px">
      <input id="chat-input" type="text" placeholder="Ask anything..."
        onkeydown="if(event.key==='Enter') sendMessage()"
        style="
          flex:1; border:2px solid #F5EDD8; border-radius:12px;
          padding:10px 14px; font-family:'Nunito',sans-serif;
          font-size:14px; font-weight:600; color:#2A1F10;
          background:#FDFAF3; outline:none;
        "
      >
      <button onclick="sendMessage()" style="
        width:40px; height:40px; border-radius:12px; border:none;
        background:#4EC5E8; color:white; font-size:18px;
        cursor:pointer; box-shadow:0 3px 0 #2FAFD4;
        display:flex; align-items:center; justify-content:center;
        transition:transform .1s;
      ">→</button>
    </div>
  </div>
</div>

<script>
// ── CONFIG ──────────────────────────────────────────────
// Replace with your actual Railway URL after deploying
const BACKEND_URL = "https://YOUR-APP.up.railway.app";

// ── STATE ───────────────────────────────────────────────
let chatOpen = false;

// ── KEEP-ALIVE PING (Wall 6 fix) ────────────────────────
// Railway free tier spins down after inactivity.
// Ping /health every 4 minutes to keep the container warm.
setInterval(() => {
  fetch(`${BACKEND_URL}/health`).catch(() => {});
}, 4 * 60 * 1000);

// ── TOGGLE ──────────────────────────────────────────────
function toggleChat() {
  chatOpen = !chatOpen;
  const win = document.getElementById("chat-window");
  win.style.display = chatOpen ? "flex" : "none";
  if (chatOpen) document.getElementById("chat-input").focus();
}

// ── SEND MESSAGE ────────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) return;

  input.value = "";
  document.getElementById("suggestions").style.display = "none";

  appendMessage(question, "user");
  const typingEl = appendTyping();

  try {
    const res = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });

    typingEl.remove();

    if (res.status === 429) {
      appendMessage("You're asking fast! Give me a moment. 😄", "bot");
      return;
    }
    if (!res.ok) {
      appendMessage("Something went wrong on my end. Try again!", "bot");
      return;
    }

    const data = await res.json();
    appendMessage(data.answer, "bot");

  } catch (err) {
    typingEl.remove();
    appendMessage("Can't reach the server right now. Try again in a moment.", "bot");
  }
}

function sendSuggestion(btn) {
  document.getElementById("chat-input").value = btn.textContent;
  sendMessage();
}

// ── DOM HELPERS ─────────────────────────────────────────
function appendMessage(text, role) {
  const msgs = document.getElementById("chat-messages");
  const div  = document.createElement("div");
  div.style.cssText = role === "user"
    ? "background:#4EC5E8;color:white;border-radius:14px 14px 4px 14px;padding:10px 14px;font-size:14px;font-weight:600;max-width:85%;align-self:flex-end;line-height:1.5;"
    : "background:white;border:2px solid #F5EDD8;border-radius:14px 14px 14px 4px;padding:10px 14px;font-size:14px;font-weight:600;color:#2A1F10;max-width:85%;line-height:1.5;";
  div.textContent = text;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function appendTyping() {
  const msgs = document.getElementById("chat-messages");
  const div  = document.createElement("div");
  div.style.cssText = "background:white;border:2px solid #F5EDD8;border-radius:14px 14px 14px 4px;padding:10px 14px;font-size:14px;color:#8A6E50;max-width:60%;";
  div.innerHTML = "Thinking<span id='dots'>.</span>";
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  // Animate dots
  let n = 1;
  div._interval = setInterval(() => {
    document.getElementById("dots").textContent = ".".repeat((n++ % 3) + 1);
  }, 400);
  div.remove = () => { clearInterval(div._interval); div.parentNode?.removeChild(div); };
  return div;
}
</script>
```

---

## Production walls I hit — documented

### Wall 1 — Docker image too large
**What happened:** Default `sentence-transformers` install pulls PyTorch with CUDA support. CUDA = ~4GB. Railway limit = 4GB total image. Build failed.

**Fix:** In `requirements.txt`, add `--extra-index-url https://download.pytorch.org/whl/cpu` and install `torch==2.3.1+cpu`. CPU-only torch is ~250MB. Total image drops to ~1.8GB.

**Proof it's fixed:** `Dockerfile` pre-downloads the model at build time. Railway build logs show final image size.

---

### Wall 2 — ChromaDB wiped on every redeploy
**What happened:** Railway's filesystem is ephemeral. Stored ChromaDB data disappeared on each deploy. The server started with an empty collection and crashed on the first `/chat` request.

**Fix:** `start.sh` runs `python ingest.py` before starting uvicorn. Every startup re-ingests from `bidoog.txt` which is committed to the repo. Takes ~15 seconds but means the knowledge base is always fresh.

---

### Wall 3 — Model re-loading on every request (15s response times)
**What happened:** `_load_resources()` was being called inside the `ask()` function instead of at startup. Every single request paid the full model load cost (~12 seconds for SentenceTransformer + ChromaDB connect).

**Fix:** Move `_load_resources()` to FastAPI's `lifespan` context manager. It runs once at startup. Module-level singletons (`_model`, `_collection`, `_gemini`) are reused on every request. Response time drops to ~1.5 seconds.

---

### Wall 4 — "Permission denied" on start.sh
**What happened:** `start.sh` was committed without the executable bit. Railway tried to run it and got: `bash: ./start.sh: Permission denied`. Container failed to start.

**Fix two ways:**
1. `RUN chmod +x start.sh` in the Dockerfile (permanent, the right fix)
2. `git update-index --chmod=+x start.sh && git commit -m "fix: executable bit"` (if you're re-committing)

---

### Wall 5 — CORS errors on live site
**What happened:** Portfolio was on Vercel (`https://bidoog.vercel.app`). Backend was on Railway (`https://bidoog-chatbot.up.railway.app`). Browser blocked all cross-domain requests. Two mistakes compounded:
1. `ALLOWED_ORIGINS` env var on Railway only had `localhost`
2. The Vercel URL was missing `https://` — just `bidoog.vercel.app` instead of `https://bidoog.vercel.app`

**Fix:** In Railway dashboard → Variables → set `ALLOWED_ORIGINS` to the exact full URL including `https://`. Check in browser Network tab: OPTIONS preflight request should return 200, not blocked.

---

### Wall 6 — Cold starts making chatbot feel broken
**What happened:** Railway free tier spins down containers after ~15 minutes of inactivity. Next request triggered a cold start: ingest + model load = 20-30 seconds before a response. Recruiters would click send and see nothing.

**Fix:** Keep-alive ping in the frontend JavaScript. Every 4 minutes, `fetch(BACKEND_URL + '/health')` fires silently. Keeps the container warm. Zero cost, zero user impact.

---

## Environment variables reference

| Variable | Where set | Example value |
|---|---|---|
| `GEMINI_API_KEY` | Railway dashboard | `AIza...` |
| `ALLOWED_ORIGINS` | Railway dashboard | `https://bidoog.vercel.app` |
| `PORT` | Auto-set by Railway | `8000` |

---

## License
MIT
