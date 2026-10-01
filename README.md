# PolicyPal — Company Policy Assistant (RAG)

PolicyPal is a web chat assistant that answers employee questions about a fictional company's (Acme Corp) policies. It retrieves the relevant policy passages, asks a language model to answer **only** from those passages, and shows numbered citations with the exact supporting snippet and a link to the source section. Questions the policies don't cover are refused.

- **Backend:** Python 3.11 + Flask (`/`, `POST /chat`, `/health`, `/sources/<doc_id>`)
- **Frontend:** React 19 + Vite, built to static files and served by Flask at `/`
- **RAG:** custom Python pipeline · Chroma (persistent, cosine) · `BAAI/bge-small-en-v1.5` embeddings · `cross-encoder/ms-marco-MiniLM-L-6-v2` re-ranking · Groq-hosted Llama (OpenAI-compatible API)
- **Langflow:** optional custom component so the flow *Chat Input → PolicyPal RAG → Chat Output* uses the same service ([langflow/README.md](langflow/README.md))
- **CI/CD:** GitHub Actions on every push and PR; Docker image deployable to Railway

Design, evaluation method and results are in [design-and-evaluation.md](design-and-evaluation.md). AI tool usage is documented in [ai-tooling.md](ai-tooling.md). The working plan and progress tracker is [PROJECT_BLUEPRINT.md](PROJECT_BLUEPRINT.md).

> **Corpus licence.** All 12 policies in `data/policies/` are original, synthetic documents written for this project (with AI assistance) about a fictional company. The team owns them and they may be committed, copied and modified freely.

---

## 1. Quick start (local)

Requirements: Python 3.11, Node.js 22 (or 20.19+), git. Commands are for macOS/Linux; Windows equivalents are noted.

```bash
git clone <your-repo-url> policypal && cd policypal

# 1. Isolated Python environment
python3.11 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. Dependencies (CPU-only torch first, to avoid the multi-GB CUDA build)
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-dev.txt

# 3. Configuration
cp .env.example .env                 # then set LLM_API_KEY (free key from console.groq.com)

# 4. Build the vector index (downloads the embedding model once, ~130 MB)
python -m app.ingest

# 5. Build the React UI
npm --prefix frontend ci
npm --prefix frontend run build

# 6. Run
flask --app app run --port 5000      # or: gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --threads 4
```

Open <http://127.0.0.1:5000>. Check health with `curl http://127.0.0.1:5000/health`.

### Running without an API key or model download

Two offline switches exist for demos, CI and environments without network access:

```bash
EMBED_BACKEND=hash LLM_PROVIDER=extractive python -m app.ingest
EMBED_BACKEND=hash LLM_PROVIDER=extractive flask --app app run --port 5000
```

`hash` is a deterministic bag-of-words embedder (no download); `extractive` answers by quoting the best-matching retrieved sentences instead of calling an LLM. Answers stay grounded and cited, but quality is lower than the real configuration — the UI shows which provider produced each answer. The index must be rebuilt whenever `EMBED_BACKEND` changes (`/health` reports `index_ready: false` otherwise).

### Frontend development with hot reload

```bash
flask --app app run --port 5000          # terminal 1
npm --prefix frontend run dev            # terminal 2 → http://localhost:5173 (proxies the API to :5000)
```

---

## 2. API

### `POST /chat`

```bash
curl -s http://127.0.0.1:5000/chat -H 'Content-Type: application/json' \
  -d '{"question": "How many unused PTO days can I carry over?"}'
```

Illustrative response (scores, provider and timings vary by configuration; this is not a measurement):

```json
{
  "status": "answered",
  "answer": "Up to 5 unused days of PTO may be carried over into the next calendar year. [1]",
  "refused": false,
  "citations": [
    {
      "id": 1, "ref": 1,
      "chunk_id": "POL-02-v1.0-s09-c00",
      "document_id": "POL-02", "doc_id": "POL-02", "document_version": "1.0",
      "title": "Paid Time Off (PTO)", "section": "Carry-over",
      "page_start": null, "page_end": null,
      "snippet": "Up to 5 unused days of PTO may be carried over into the next calendar year. Carried-over days must be used by 31 March of that year.",
      "source_url": "/sources/POL-02#carry-over", "url": "/sources/POL-02#carry-over"
    }
  ],
  "corpus_version": "v1-2a44e4aa53",
  "provider": "groq:llama-3.1-8b-instant",
  "truncated": false,
  "retrieval": {"best_similarity": 0.81, "threshold": 0.35, "reranked": true, "chunks": ["…"]},
  "request_id": "req-3f2a9c1d7b44",
  "latency_ms": 1840
}
```

The request may use `question` or Langflow's `input_value`, plus an optional `session_id` that is echoed back. Each question is answered independently (no conversation memory).

| HTTP | `status` | Meaning |
|---|---|---|
| 200 | `answered` | Evidence-backed answer with ≥ 1 valid citation |
| 200 | `insufficient_evidence` | On-topic, but the retrieved policies don't contain the answer (`refused: true`) |
| 200 | `out_of_scope` | Nothing in the corpus is relevant; refused before calling the LLM (`"I can only answer about our policies."`) |
| 400 | `invalid_request` | Missing/empty question, > 2,000 characters, malformed JSON, or file attachments |
| 503 | `knowledge_base_unavailable` | Index missing or built with different embedding settings |
| 502 | `provider_error` | LLM provider failed (after one retry and the optional fallback provider) |
| 504 | `provider_timeout` | LLM provider exceeded `LLM_TIMEOUT_S` |

### Other routes

- `GET /` — chat UI (React build).
- `GET /health` — `{"status":"ok","index_ready":true,"index_loaded":false,"chunks":203,"documents":12,"corpus_version":"…","embed_backend":"…","llm_provider":"…","version":"1.0.0"}`. Cheap: never calls the LLM.
- `GET /sources/<doc_id>` (alias `/docs/<doc_id>`) — serves a registered policy. PDFs are served as PDF (citations link to `#page=N`); md/txt/html are rendered with section anchors (citations link to `#section-anchor`). Unknown IDs return 404.
- `GET /api/policies` — policy list and example questions for the UI sidebar.

---

## 3. Project layout

```text
app/                    Flask app and RAG pipeline
  __init__.py           create_app(); `app` WSGI object (gunicorn app:app)
  config.py             all settings, read from env / .env; fixed seeds
  parsing.py            md / txt / html / pdf parsers and cleaning
  chunking.py           heading-first chunking, 500-token windows, 75 overlap
  embeddings.py         bge-small (sentence-transformers) or offline hash embedder
  vectorstore.py        persistent Chroma collection + index metadata
  ingest.py             `python -m app.ingest` - idempotent index rebuild
  retriever.py          top-k cosine → cross-encoder re-rank → top-n
  generator.py          evidence-only prompt; Groq/OpenRouter/OpenAI client; extractive fallback
  guardrails.py         input validation, refusals, output-length cap
  citations.py          [n] marker → citation mapping, verbatim snippets
  rag.py                pipeline orchestration and lazy loading
  routes.py, sources.py HTTP routes and source rendering
frontend/               React + Vite chat UI (src/, built to dist/)
data/policies/          12 synthetic policies (md, txt, html, pdf)
data/pdf_sources/       Markdown sources for the 3 PDFs (scripts/build_pdfs.py)
data/manifest.json      corpus manifest: ids, versions, page counts, sha256, provenance
eval/                   questions.jsonl, run.py, results/
langflow/               Langflow custom component + instructions
scripts/                build_pdfs.py, build_manifest.py, calibrate_threshold.py, download_models.py
tests/                  offline pytest suite (no API key or download needed)
.github/workflows/ci.yml
Dockerfile, railway.json
```

---

## 4. Tests and CI

```bash
EMBED_BACKEND=hash pytest            # 53 tests: parsing, chunking, index rebuild, retrieval,
                                     # citations, guardrails, API contract, error paths, sources
npm --prefix frontend test           # UI helpers (citation parsing, escaping)
```

The tests build their own temporary index with the offline embedder and replace the LLM with fakes, so they never need a key or network access.

`.github/workflows/ci.yml` runs on every push and pull request:

1. **backend** — install dependencies (CPU torch + `requirements-dev.txt`), `import app`, verify `data/manifest.json` is current, build the index, run `pytest`, then start gunicorn and check `/health` and a real `POST /chat`.
2. **frontend** — `npm ci`, `npm test`, `npm run build`.
3. **deploy** (push to `main` only) — runs `railway up` if a `RAILWAY_TOKEN` secret exists; otherwise it skips with a message.

---

## 5. Evaluation

```bash
# terminal 1: run the configuration you want to measure
gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --threads 4
# terminal 2
python -m eval.run --url http://127.0.0.1:5000 --name groq-bge-rerank
```

Outputs go to `eval/results/<name>/`: `summary.md`, `summary.json`, `results.jsonl` (every answer and citation), `latency.csv` and `review_sheet.csv` for human scoring. Set `JUDGE_PROVIDER`, `JUDGE_API_KEY` and `JUDGE_MODEL` (a different model from the generator) to score groundedness with an LLM judge; otherwise a lexical support proxy is used and labelled. `python scripts/calibrate_threshold.py` suggests a `SCORE_THRESHOLD` for the active embedder. See [design-and-evaluation.md](design-and-evaluation.md) for targets and recorded results.

---

## 6. Deploying to Railway

The repository includes a `Dockerfile` and `railway.json`. The image builds the React app, installs CPU-only PyTorch, downloads both models and builds the Chroma index at build time, so a container starts ready to answer.

1. Push the repository to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo** and pick the repository. Railway detects `railway.json` and builds the Dockerfile.
3. In the service's **Variables**, set at least `LLM_API_KEY` (and optionally `LLM_PROVIDER`, `LLM_MODEL`, `LLM_FALLBACK_*`, `SCORE_THRESHOLD`). Do not set `PORT`; Railway provides it.
4. Under **Settings → Networking**, generate a public domain. The health check uses `/health`.
5. Optional: enable "Wait for CI" in the service's deploy settings, or add a `RAILWAY_TOKEN` repository secret (and a `RAILWAY_SERVICE` repository variable) so the CI `deploy` job deploys after tests pass.

Memory: the two models plus PyTorch need roughly 1–1.5 GB RAM. If the plan's memory is too small, build with `--build-arg EMBED_BACKEND=hash`, set `EMBED_BACKEND=hash` and `RERANK=0` (lower retrieval quality), or move to a larger instance. Record the public URL in [deployed.md](deployed.md).

---

## 7. Configuration reference

All settings are environment variables (see `.env.example`). The most important:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq`, `openrouter`, `openai` or `extractive` (offline) |
| `LLM_API_KEY` / `LLM_MODEL` | – / `llama-3.1-8b-instant` | Provider key and model (free model lists change; keep it in env) |
| `LLM_FALLBACK_PROVIDER` / `_API_KEY` / `_MODEL` | – | Second provider used when the first fails |
| `EMBED_BACKEND` / `EMBED_MODEL` | `sentence-transformers` / `BAAI/bge-small-en-v1.5` | Embeddings; `hash` for offline |
| `RERANK` | on for sentence-transformers | Cross-encoder re-ranking |
| `TOP_K` / `TOP_N` | 8 / 4 | Candidates retrieved / passages given to the LLM |
| `SCORE_THRESHOLD` | 0.35 (bge) · 0.12 (hash) | Below this best similarity, refuse without calling the LLM |
| `CHUNK_TOKENS` / `CHUNK_OVERLAP` | 500 / 75 | Chunking (tokens ≈ words) |
| `MAX_QUESTION_CHARS` | 2000 | Input limit |
| `ANSWER_WORD_TARGET` / `MAX_ANSWER_WORDS` / `MAX_TOKENS` | 150 / 250 / 300 | Prompted length / hard cap verified after generation / provider token cap |
| `SEED` | 42 | Seeds Python, NumPy, torch and the provider `seed` parameter |

## 8. Updating the corpus

1. Edit or add files in `data/policies/` (for PDFs, edit `data/pdf_sources/*.md` and run `python scripts/build_pdfs.py`). Every file needs `doc_id`, `title`, `version` and `effective_date` metadata.
2. `python scripts/build_manifest.py` — refreshes hashes and page counts.
3. `python -m app.ingest` — rebuilds the index; ingestion refuses to run if a file changed without a manifest update.
