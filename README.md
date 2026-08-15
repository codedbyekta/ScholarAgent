# ScholarAgent — Autonomous Research Assistant with Quantifiable Evaluation

A full-stack agentic AI system: **React + Vite + Tailwind** (frontend, deployed on **Vercel**) +
**FastAPI + Python** (backend, deployed on **Render**) + **LangGraph** (agent orchestration) +
**Gemini via the Google GenAI SDK** (LLM + embeddings) + **Chroma** (local vector DB) +
**SQLite** (memory + evaluation storage) + **PyMuPDF** (PDF parsing). No Docker.

Ask a research question; the agent plans sub-questions, searches arXiv + Semantic Scholar,
retrieves from your own uploaded PDFs (RAG), verifies recency via live web search, writes a
cited Markdown answer, then **verifies every claim against its actual source** and reports
which claims are supported vs. unsupported.

A built-in **Evaluation Dashboard** runs a reproducible 10-question benchmark against the real
pipeline (no mocks) and reports 5 quantifiable metrics.

---

## Architecture

```
React (Vercel) --> FastAPI (Render) --> LangGraph agent
                                          |
             +----------------------------+----------------------------+
             |              |              |                           |
        Tool 1: papers  Tool 2: RAG   Tool 3: web search       Tool 4: citation
        (arXiv +        (Chroma,      (Tavily / DuckDuckGo)    verification
        Semantic         user's                                (claim extraction +
        Scholar)         uploaded PDFs)                         LLM-judged verdict)
```

**Exactly 4 tools**, used by these LangGraph nodes:

```
planner -> paper_retrieval (Tool 1) -> rag_retrieval (Tool 2)
        -> web_verification (Tool 3) -> synthesizer
        -> claim_verification (Tool 4) -> citation_formatter
```

---

## Folder Structure

```
scholaragent/
├── backend/
│   ├── requirements.txt
│   ├── render.yaml
│   ├── .env.example
│   ├── tests/                        # pytest suite (23 tests, no API key needed)
│   └── app/
│       ├── main.py                   # FastAPI entrypoint
│       ├── core/
│       │   ├── config.py             # single source of settings
│       │   ├── logging_config.py
│       │   └── llm_client.py         # Gemini via google-genai SDK
│       ├── db/
│       │   ├── sqlite_db.py          # sessions, chat memory, eval runs
│       │   └── chroma_store.py       # local vector DB (no server)
│       ├── services/
│       │   └── pdf_ingest.py         # PyMuPDF extraction + chunking
│       ├── tools/                    # the 4 agent tools
│       │   ├── paper_search_tool.py      # Tool 1
│       │   ├── rag_tool.py               # Tool 2
│       │   ├── web_search_tool.py        # Tool 3
│       │   ├── citation_verification_tool.py  # Tool 4
│       │   └── citation_registry.py      # deterministic formatting (not a tool)
│       ├── agent/
│       │   ├── state.py, prompts.py, nodes.py, graph.py
│       ├── eval/
│       │   ├── benchmark.json        # 10 questions + ground truth
│       │   ├── metrics.py            # all 5 metric formulas
│       │   ├── eval_engine.py        # runs the REAL pipeline, no mocks
│       │   └── run_eval.py           # reproducible CLI command
│       ├── models/schemas.py
│       └── api/
│           ├── routes_chat.py, routes_documents.py, routes_health.py, routes_eval.py
│
└── frontend/
    ├── package.json, vite.config.js, tailwind.config.js, vercel.json
    └── src/
        ├── App.jsx                   # Chat / Evaluation tab switch
        ├── api/client.js
        └── components/
            ├── ChatView.jsx, MessageBubble.jsx, ToolTrace.jsx, FileUpload.jsx
            └── EvalDashboard.jsx, MetricCard.jsx, BarChart.jsx
```

---

## Running Locally (no Docker)

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set GOOGLE_API_KEY (get one free at aistudio.google.com/apikey)

uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000** (Swagger docs at `/docs`). SQLite and Chroma both
write to `backend/app/data/` automatically on first run — no separate servers to start.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend runs at **http://localhost:5173**.

### 3. Run the tests

```bash
cd backend
pytest tests/ -v
```

All 23 tests run with **zero network calls and zero API key** — they test the metric formulas,
citation formatting, and PDF chunking logic in isolation.

### 4. Run the evaluation (reproducible command)

```bash
cd backend
python -m app.eval.run_eval
```

This is the exact same code path the "Run Evaluation" button in the frontend calls
(`POST /api/eval/run`) — both call `run_full_evaluation()` in `app/eval/eval_engine.py`.
It prints aggregate metrics to stdout and saves a timestamped JSON report to
`backend/app/data/eval_reports/`.

---

## The 5 Evaluation Metrics — Exact Formulas

Every metric below is computed **only from real pipeline runs**. If a run fails (missing API
key, network error, zero claims extracted, etc.), the affected question is excluded from
averages and the dashboard displays **"Not evaluated"** instead of a fabricated number — see
`metrics.py`, every function returns `None` rather than `0` when there's nothing to measure.

### 1. Retrieval Precision@K
```
Precision@K = (# of top-K retrieved papers matching a ground-truth source) / K
```
Ground truth: each of the 10 benchmark questions lists `expected_sources` — keyword(s) from a
well-known seminal paper's title (e.g. "Attention Is All You Need" for the Transformer
question). A retrieved paper "matches" if its title contains the keyword (case-insensitive).
K defaults to 5 (`EVAL_TOP_K` in `.env`) and is **also adjustable live in the dashboard** — the
slider recomputes Precision@K client-side from the same run's actually-retrieved paper titles,
so every K value you see still traces back to one real API call.

### 2. Retrieval Success Rate
```
Success Rate = (# questions where AT LEAST ONE retrieved paper matched) / (total questions)
```
Looser than Precision@K — checks the full retrieved list, not just the top K.

### 3. Citation Verification Accuracy
```
Accuracy = (# claims WITH a citation that were verified SUPPORTED) / (# claims WITH a citation)
```
For every generated answer, `citation_verification_tool.py` (1) extracts atomic claims via an
LLM call, tagging each with the citation numbers it used, then (2) for each claim, feeds the
**actual text of the cited source** back to the LLM and asks it to judge, strictly from that
text, whether the claim is accurate. This is what makes the accuracy number meaningful — it's
not "did the agent cite something," it's "did we check the citation against the real source and
confirm it holds up."

### 4. Unsupported Claim Rate
```
Unsupported Rate = (# claims verdict=UNSUPPORTED, including uncited claims) / (total claims)
```
Broader denominator than metric 3 — this one counts *every* claim the answer made, including
ones with no citation at all (which are always UNSUPPORTED by definition).

### 5. Response Latency
```
average_ms = sum(latency per question) / (# successful questions)
min_ms / max_ms = fastest / slowest single question
```
Measured with `time.perf_counter()` wrapped tightly around the full `graph.invoke()` call for
each question — i.e. total wall-clock time for the entire 7-node pipeline (planning, 3 retrieval
tool calls, synthesis, claim verification, formatting), not just the LLM call.

---

## What Counts as "Not Evaluated"

- No `GOOGLE_API_KEY` configured → the whole run is refused before it starts; dashboard shows
  the reason, not a fake score.
- A specific question's pipeline run throws an exception (network failure, API timeout) → that
  question is recorded with `error` set, excluded from all averages, and shown as "failed" in
  the per-question table.
- Zero claims were extracted from an answer (e.g. the model gave a hedge-only response) →
  `citation_verification_accuracy` and `unsupported_claim_rate` return `None` for that question,
  displayed as "Not evaluated" rather than 0% or 100%.

---

## Deployment

### Backend → Render

1. Push this repo to GitHub.
2. In Render, "New +" → "Blueprint" → point at this repo (it will read `backend/render.yaml`).
3. Set the `GOOGLE_API_KEY` secret in the Render dashboard (marked `sync: false` in the blueprint,
   so it's not stored in the repo).
4. Render mounts a persistent disk at `backend/app/data` so SQLite + Chroma data survive restarts.

### Frontend → Vercel

1. In Vercel, "Add New Project" → import this repo, set root directory to `frontend`.
2. Vercel auto-detects Vite via `vercel.json`.
3. Set environment variable `VITE_API_URL` to your Render backend URL
   (e.g. `https://scholaragent-backend.onrender.com`).
4. Update `CORS_ORIGINS` in the backend's Render env vars to include your Vercel URL.

---

## Required API Keys

| Key | Required? | Where to get it |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | aistudio.google.com/apikey |
| `TAVILY_API_KEY` | Optional (better web search; falls back to DuckDuckGo) | tavily.com |
