# Requirements compliance

This document maps every requirement in the *AI Engineering Project* brief, and every criterion of the score-5 rubric, to where it is met in this repository. Each line names the evidence a reviewer can open or run.

**Repository status key:** ✅ done and evidenced in the repository · 🟡 done, but the evidence is produced outside the repository (to be confirmed by the team before submission).

**Quick links:** [README](README.md) · [Design and evaluation](design-and-evaluation.md) · [AI tooling](ai-tooling.md) · [Deployment](deployed.md) · [Project inputs](docs/project-inputs.md) · [GitHub Actions guide](docs/github-actions.md) · Live app: <https://policypal-8u6n.onrender.com>

---

## 1. Project description requirements

| Requirement (brief) | Status | How we meet it | Evidence |
|---|---|---|---|
| Corpus of about 5–20 policy files (md/HTML/PDF/TXT), 30–120 pages | ✅ | 12 policies: 5 Markdown, 2 text, 2 HTML, 3 PDF; 10,928 words, 32 pages / page-equivalents | `data/policies/`, `data/manifest.json`, `tests/test_ingest.py::test_manifest_meets_corpus_requirements` |
| Corpus can legally be included | ✅ | Original synthetic policies for a fictional company, written for this project; provenance and permission recorded per document | `data/manifest.json` (`provenance`, `permission_status`), README |
| Success metrics defined: ≥1 information-quality and ≥1 system metric | ✅ | Groundedness, citation accuracy, citation validity, partial match, refusal accuracy (quality); p50/p95 latency (system), each with a target | `design-and-evaluation.md` §5 |
| Free or zero-cost services | ✅ | Groq free tier (LLM), local ONNX embeddings, local Chroma, Render free tier, GitHub Actions | `render.yaml`, `.env.example` |

## 2. Steps 1–8 of the brief

### Step 1 — Environment and reproducibility

| Requirement | Status | Evidence |
|---|---|---|
| Virtual environment | ✅ | README §4 (`python -m venv .venv`); `scripts/setup_offline.ps1` / `.sh` |
| Dependencies listed | ✅ | `requirements.txt` (full), `requirements-lite.txt` (ONNX, no PyTorch), `requirements-dev.txt`, `frontend/package-lock.json` |
| README with setup and run instructions | ✅ | `README.md` §1 and §4 (Windows and macOS/Linux) |
| Fixed seeds | ✅ | `SEED=42` seeds Python, NumPy, torch (if loaded) and the LLM `seed` parameter (`app/config.py::set_seeds`); sorted file order; deterministic PDFs; index metadata records seed and settings (`storage/chroma/index_meta.json`) |

### Step 2 — Ingestion and indexing

| Requirement | Status | Evidence |
|---|---|---|
| Parse and clean PDF/HTML/md/txt | ✅ | `app/parsing.py`: HTML navigation, scripts and footers removed; PDF running headers/footers removed; real PDF page numbers kept. Tests: `test_every_policy_parses_with_metadata`, `test_html_cleaning_strips_navigation_and_scripts`, `test_pdf_keeps_real_pages_and_removes_running_headers` |
| Chunk by headings or token windows with overlap | ✅ | `app/chunking.py`: headings first, then 500-token windows with 75-token overlap; stable chunk IDs. Test: `test_chunks_respect_size_overlap_and_ids` |
| Embed with a free model | ✅ | ONNX `all-MiniLM-L6-v2` (384-dim, local, no API cost); `sentence-transformers` and an offline hash embedder also supported (`app/embeddings.py`) |
| Store in a local/lightweight vector database | ✅ | **Chroma** persistent client, cosine distance, in `storage/chroma/` (`app/vectorstore.py`). Rebuild: `python -m app.ingest`. Test: `test_rebuild_is_idempotent_and_reuses_embeddings` |

### Step 3 — Retrieval and generation (RAG)

| Requirement | Status | Evidence |
|---|---|---|
| Framework or manual implementation | ✅ | Manual (plain Python), as allowed; reasons in `design-and-evaluation.md` §2 |
| Top-k retrieval with optional re-ranking | ✅ | Top 8 by cosine → top 4 to the LLM; optional cross-encoder re-ranker (`RERANK=1`) (`app/retriever.py`). Tests: `test_expected_document_is_retrieved` |
| Prompt injects retrieved chunks with sources | ✅ | Numbered passages `[1] (POL-02 · Paid Time Off · Carry-over …)` in a delimited `<context>` block (`app/generator.py::build_messages`). Test: `test_prompt_delimits_untrusted_text` |
| Guardrail: refuse outside the corpus ("I can only answer about our policies") | ✅ | Similarity threshold refuses before the LLM is called; the prompt's `INSUFFICIENT_EVIDENCE` rule handles in-topic gaps. Tests: `test_out_of_scope_is_refused_without_calling_the_llm`, `test_model_refusal_becomes_insufficient_evidence`; eval refusal accuracy 100% (5/5) |
| Guardrail: limit output length | ✅ | ≤150 words in the prompt, `MAX_TOKENS=300`, 250-word hard cap at sentence boundaries. Tests: `test_long_answer_is_capped`, `test_word_cap_cuts_at_sentence_boundaries` |
| Guardrail: always cite source doc IDs/titles | ✅ | Answers without a valid citation are retried once, then refused; citations built from stored metadata. Tests: `test_uncited_answer_is_retried_then_refused`, `test_markers_are_mapped_renumbered_and_invalid_ones_dropped` |

### Step 4 — Web application

| Requirement | Status | Evidence |
|---|---|---|
| Flask, Streamlit or alternative | ✅ | Flask 3 + React 19 (Vite) |
| `/` web chat with text box | ✅ | React chat with example questions, citation buttons, expandable source cards and refusal/error states. Live: <https://policypal-8u6n.onrender.com> |
| `POST /chat` returns answer, citations, snippets, source links | ✅ | `app/routes.py`; each citation has document ID, title, section, page/anchor, exact snippet (≤300 characters) and `source_url`. Tests: `test_chat_returns_answer_citations_and_snippets`, `test_every_citation_link_resolves` |
| `/health` returns JSON status | ✅ | `{"status":"ok","index_ready":true,"chunks":203,…}`. Tests: `test_health_reports_ready_index`, `test_health_when_index_missing` |

### Step 5 — Deployment (optional)

| Requirement | Status | Evidence |
|---|---|---|
| Free-tier host | ✅ | Render free web service (`render.yaml`, `Dockerfile.render`); Railway alternative (`Dockerfile`) |
| Environment variables for keys and endpoints | ✅ | `LLM_API_KEY`, `ADMIN_TOKEN` and others set in Render, never committed (`.gitignore` excludes `.env`; `.env.example` has placeholders) |
| Publicly accessible URL | 🟡 | <https://policypal-8u6n.onrender.com>, recorded in `deployed.md`. Confirm `/health` shows `"index_ready": true` before submitting |

### Step 6 — CI/CD

| Requirement | Status | Evidence |
|---|---|---|
| GitHub Actions on push/PR | ✅ | `.github/workflows/ci.yml` (`on: push, pull_request, workflow_dispatch`) |
| Installs dependencies | ✅ | Python 3.11 + pip cache; Node 22 + `npm ci` |
| Build/start check | ✅ | Import check, manifest check, strict index build, 73 pytest tests, gunicorn start with live `/health` and `/chat` calls, runtime policy upload; frontend tests and build |
| Optional: deploy from `main` on success | ✅ | `deploy` job calls the Render deploy hook (`RENDER_DEPLOY_HOOK` secret) after both jobs pass; see `docs/github-actions.md` |
| A green run on GitHub | 🟡 | Open the Actions tab and link the latest green run in the demo |

### Step 7 — Evaluation

| Requirement | Status | Evidence |
|---|---|---|
| 15–30 questions across topics | ✅ | 28 questions (`eval/questions.jsonl`): 21 direct (all 12 policies: PTO, holidays, sick leave, remote work, expenses, security, IT use, privacy, conduct, reviews, benefits, handbook), 2 multi-document, 2 missing-evidence, 2 out-of-scope, 1 prompt injection |
| Groundedness | ✅ | 100% human-reviewed (23/23); automated lexical proxy 73.9% with the six flagged answers reviewed (`design-and-evaluation.md` §6–7, `review_sheet.csv`) |
| Citation accuracy | ✅ | 100% (23/23); citation validity 100% (every snippet is exact stored text) |
| Exact/partial match (optional) | ✅ | 95.7% (22/23) against short gold answers |
| Latency p50/p95 over 10–20 queries | ✅ / 🟡 | Local: p50 790 ms, p95 954 ms (`eval/results/onnx-groq-final/latency.csv`). Deployed run: record in `deployed.md` |
| Ablations (optional) | ✅ (partial) | Offline baseline (hash + extractive) vs production (ONNX + Groq) compared in `design-and-evaluation.md` §6; `TOP_K`, `RERANK` and `CHUNK_TOKENS` are configurable for further runs |

### Step 8 — Design documentation

| Requirement | Status | Evidence |
|---|---|---|
| Justify embedding model, chunking, k, prompt format, vector store | ✅ | `design-and-evaluation.md` §2 (technology table with alternatives), §3 (chunking, retrieval and k, prompt, citations, guardrails, reproducibility, policy updates) |

## 3. Submission guidelines

| Item | Status | Evidence / action |
|---|---|---|
| GitHub repository with all code | ✅ | This repository |
| Shared with `quantic-grader` | 🟡 | GitHub → Settings → Collaborators → add `quantic-grader` |
| `README.md` with setup and run instructions | ✅ | `README.md` |
| `design-and-evaluation.md` (decisions and reasons; evaluation approach and results) | ✅ | `design-and-evaluation.md` |
| `ai-tooling.md` (tools, how used, what worked and what didn't) | ✅ | `ai-tooling.md` |
| Optional `deployed.md` | ✅ | `deployed.md` |
| Demo video, 5–10 minutes, screen share with voiceover; all members on camera and speak; government ID shown | 🟡 | Script in §5 below |
| Single PDF with the two links | 🟡 | `python scripts/make_submission_pdf.py --repo <url> --video <url> --admin-token <token>` (see §6) |

## 4. Rubric: score 5 criteria

| Score-5 criterion | What we did |
|---|---|
| **Addresses all of the project requirements** | Every brief item above is met (the 🟡 items are submission-time actions, not missing features). Extras beyond the brief: runtime policy updates, Langflow integration, offline mode, provider fallback. |
| **Outstanding RAG application with correct responses and matching citations; ingest and indexing work** | 100% citation accuracy and 100% citation validity on 28 questions; 95.7% partial match; 100% correct refusals including prompt injection. Citations link to the exact section, or PDF page, of the source. Ingestion handles all four formats, is idempotent, verifies hashes, and re-embeds only changed chunks. |
| **Excellent, well-structured architecture** | Separate modules for parsing, chunking, embeddings, vector store, corpus, ingestion, retrieval, generation, guardrails, citations, orchestration, admin and routes (`app/`); citations built from trusted metadata; read/write lock between chat and re-indexing; configuration only through environment variables; React frontend compiled and served by Flask (one deployable service). |
| **Public deployment fully functional** (optional) | Live on Render with the ONNX + Groq configuration, the index built into the image, a health check, and secrets in environment variables. |
| **CI/CD runs on push/PR** | Three-job workflow: backend (install, import, manifest, strict ingest, 73 tests, live server checks including a policy upload), frontend (tests and build), deploy (Render hook on `main`). |
| **Excellent documentation of design choices** | Technology table with reasons and alternatives; sections on chunking, retrieval, prompt, citations, guardrails, provider resilience, reproducibility and policy updates; known limitations; planning documents explained in `docs/project-inputs.md`. |
| **Excellent evaluation results including groundedness, citation accuracy and latency** | Defined metrics and targets; 28-question set with gold answers; all targets met (groundedness 100% human-reviewed, citation accuracy 100%, p50 0.79 s / p95 0.95 s); raw results, latency CSV and review sheet committed; limitations of the automatic proxy discussed. |
| **Excellent, clear demo of features, design and evaluation** | See the demo plan below. |

## 5. Demo plan (5–10 minutes)

| Time | Segment | Show |
|---|---|---|
| 0:00–0:45 | Team introduction | Each member on camera, says their name and role, shows government ID |
| 0:45–2:30 | The app | Live URL; ask 2–3 policy questions; click a citation → source card → **View source**; ask a multi-policy question; ask an off-topic question and a prompt-injection question (refusals) |
| 2:30–3:30 | Policy update | `/admin`: ask *"Can I bring my dog to the office?"* (refused) → upload POL-14 Pets in the Workplace → ask again (cited answer) → Reset |
| 3:30–5:00 | Design | Architecture diagram; ingestion (parse, chunk, ONNX embeddings, Chroma); retrieval threshold and top-k; evidence-only prompt; citations from metadata; guardrails |
| 5:00–6:30 | Evaluation | Question set; metrics table; human review of the proxy's flagged answers; latency |
| 6:30–7:30 | CI/CD | GitHub Actions: a green run, its steps, the deploy job; Render deploy log |
| 7:30–8:30 | AI tooling and wrap-up | How the spec, blueprint and requirements were given to the AI; what the team changed (ONNX, rate limits); lessons |

Every member must speak during the video.

## 6. Final checklist before submitting

- [ ] Push the latest code; the GitHub Actions run on `main` is green.
- [ ] Render shows **Live**; `/health` shows `"index_ready": true` and `"embed_backend": "onnx"`.
- [ ] `ADMIN_TOKEN` is set on Render; `/admin` sign-in works; policies are reset to the originals.
- [ ] Deployed latency recorded in `deployed.md`.
- [ ] Human-review columns filled in for all answered questions in `eval/results/onnx-groq-final/review_sheet.csv`.
- [ ] `ai-tooling.md`: any other AI tools the team used are added.
- [ ] Repository shared with `quantic-grader`.
- [ ] Demo recorded (5–10 minutes, all members on camera with ID) and uploaded with a shareable link.
- [ ] Submission PDF generated with the repository link, video link and admin token, then submitted by one team member.
