# Company Policy Assistant — Development Blueprint & Tracker

**Document version:** 0.2  
**Last updated:** 2026-10-01  
**Project Document:** Mathew Muwomo  
**Collaborating developer:** Munashe Sibanda  
**Current stage:** Implementation — first complete build in repository; production-model evaluation, CI run on GitHub, deployment and demo pending  
**Delivery progress:** 3/8 milestones complete (37.5%) — M2, M3, M6

> Keep this file in the repository as `PROJECT_BLUEPRINT.md`. It is the team's working source of truth for scope, decisions, tasks, interfaces and evidence of completion. Update it in the same pull request as the work it describes. The official assignment brief takes precedence over this document.

## 1. Important source clarification

This blueprint follows the supplied conversation about an **AI Engineering RAG policy chatbot**. The attached `ProjectDocument.pdf` is actually the **Managing Software Engineering / Lily's Florist** brief. It does not verify the chatbot assignment requirements.

- **Reported assignment requirement (R):** Described in the supplied AI-project conversation; verify against the correct official brief before treating it as confirmed.
- **Proposed implementation choice (P):** A practical recommendation for the team to adopt or revise.
- **Optional enhancement (O):** Not required for the planned first release.

Do not merge the florist project's 15 user stories, 20 requirements, Figma deliverables or four-page submission structure into this chatbot assignment unless the correct AI brief explicitly requires them.

| Source | Status | Action |
|---|---|---|
| Supplied AI-project conversation | Available; secondary account of brief | Used to draft reported requirements below |
| Attached `ProjectDocument.pdf` | Reviewed; belongs to Lily's Florist | Keep separate from this project |
| Correct AI Engineering project brief | Requirements text supplied in the team chat (2026-10-01, `attachment.txt`) and reconciled below; official brief link still to be attached | Attach official link (T01) |
| Repository and existing implementation | v0.2 build created 2026-10-01 (this repository) | Push to GitHub, add URL (T02) |
| Product Spec: PolicyPal RAG Assistant (Munashe Sibanda, 2026-10-01) | Available; used for stack, corpus plan, metrics and targets | Spec choices recorded as decisions D01–D12 |

## 2. Product goal and boundaries

Build a web application that helps employees answer questions about company policies. It retrieves relevant policy passages, generates a concise answer from that evidence, and displays citations, snippets and source links. It explains when the available documents cannot answer a question.

**Core user journey:** Open app → ask a policy question → receive answer → inspect citation → open supporting policy section.

**First-release scope:** Fixed, permission-cleared policy corpus; ingestion and retrieval; evidence-based answers; source viewing; chat UI; required endpoints; evaluation; CI; documentation; demonstration.

**Deferred scope (O):** Employee authentication, user uploads, role-specific document permissions, HR integrations, approval workflows, persistent conversation accounts, multilingual support and public hosting. Add these only through a recorded scope decision.

**Conversation behavior (P):** Each request is self-contained. The UI may display earlier messages, but follow-up questions must repeat relevant context. Multi-turn reasoning is deferred and must not be implied by the interface.

## 3. Shared working rules

1. Read this file before starting a task. Claim a task ID and record an owner.
2. Use stable requirement IDs (`R01`), task IDs (`T01`), decision IDs (`D01`) and evaluation IDs (`Q01`). Never reuse retired IDs.
3. Check a task only when its acceptance condition passes. Link the PR, test output or artifact in the evidence register.
4. A milestone is complete only when every required task and its exit gate pass. Update the dashboard and progress log together.
5. Record scope or interface changes here before dependent code diverges. Keep API examples, implementation and tests consistent.
6. Leave unknowns explicit. Do not invent deadlines, links, evaluation results or completion status.
7. Use PR review for shared changes. One developer owns a task; the other reviews its relevant behavior.
8. Record AI assistance as it occurs, including important corrections and failed suggestions.

**Status vocabulary:** Not started / In progress / Blocked / In review / Complete.  
**Progress calculation:** Completed milestones ÷ 8 × 100. This measures delivery gates, not hours spent or estimated effort.  
**Update trigger:** Every merged task, blocker, changed decision or evaluation run. Increment the document version when scope or interfaces change.

## 4. Requirements and verification matrix

All entries marked R below are **reported and awaiting official-brief verification**. Team choices marked P are acceptance criteria for the proposed implementation, not Quantic-imposed thresholds.

| ID | Type | Requirement | Verification / evidence | Milestone |
|---|---|---|---|---|
| R01 | R / Data | Provide 5–20 permitted policy documents totaling approximately 30–120 pages. Fictional AI-assisted policies were reported as acceptable. | Corpus manifest, page count, permission/provenance record | M2 |
| R02 | R / Ingestion | Parse, clean and split documents into searchable chunks. | Inspect sampled chunks against originals | M3 |
| R03 | R / Retrieval | Generate embeddings and store them in a local or lightweight vector database. | Index build and retrieval evidence | M3–M4 |
| R04 | R / Generation | Generate answers from retrieved policy evidence. | Groundedness review across evaluation set | M5–M7 |
| R05 | R / Attribution | Return citations, supporting snippets and source links or locations. | Every cited passage resolves to its original source | M5–M6 |
| R06 | R / Safeguards | Limit answer length and decline unsupported or outside-scope questions. | Boundary-case tests and measured output length | M5 |
| R07 | R / UI | Provide a working chat interface at `/`. | Browser walkthrough | M6 |
| R08 | R / API | Provide POST `/chat` returning answer, citations and snippets. | API contract tests | M6 |
| R09 | R / API | Provide `/health` returning a simple JSON status. | Endpoint check | M6 |
| R10 | R / Reproducibility | Include isolated setup, dependency file, run instructions and fixed seeds where applicable. | Fresh-environment walkthrough | M7 |
| R11 | R / CI | Run GitHub Actions on pushes and pull requests, installing dependencies and performing a build/import/startup check. | Successful workflow linked to commit | M7 |
| R12 | R / Evaluation | Evaluate 15–30 policy questions and report groundedness and citation accuracy. | Versioned question set and scored results | M7 |
| R13 | R / Performance | Report p50/p95 response latency measured across 10–20 queries. | Raw timings, method and percentile calculation | M7 |
| R14 | R / Documentation | Include `README.md`, `design-and-evaluation.md` and `ai-tooling.md`. | Peer review against actual implementation | M8 |
| R15 | R / Demonstration | Record a 5–10-minute screen-share demo covering app, design, evaluation and CI. | Video length/content/access check | M8 |
| R16 | R / Submission | Submit a PDF linking repository and demo; share repository with `quantic-grader`. | Verify exact submission/access instructions in correct brief | M8 |
| R17 | P / Traceability | Preserve document ID, title, section, page/location, chunk ID and corpus version for evidence. | Metadata checks and source-opening test | M3–M6 |
| R18 | P / Reliability | Return clear errors for malformed input, unavailable index and provider failure. | API tests and UI error walkthrough | M5–M6 |
| R19 | P / Usability | Support mobile layout, keyboard input, visible focus and readable source cards. | Manual desktop/mobile/keyboard review | M6 |
| R20 | P / Security | Keep secrets server-side, escape displayed content and restrict source links to known corpus documents. | Review plus targeted tests | M5–M7 |
| R21 | P / Maintenance | Version corpus, retrieval configuration, prompts and evaluation results. | Reproduce a recorded evaluation configuration | M7 |

**Reported optionality:** LangChain is recommended but optional; manual RAG is allowed. Public hosting, automated deployment and extra experimental comparisons were reported as optional. Verify these statements against the correct brief.

**Reported participant conditions:** Individual or group of up to three; all participants speak, appear on camera and show government ID in the demonstration. Verify the exact ID-handling and video-sharing instructions before recording; do not store ID images in the source repository.

## 5. Architecture and proposed stack

Use a single application with clear module boundaries. v0.2 decisions (see §11): Flask API + React (Vite) UI served by Flask, plain-Python RAG pipeline (spec) instead of LangChain, Langflow integration via a custom component.

| Component | Proposed choice (P) | Purpose / decision status |
|---|---|---|
| Backend | Python 3.11 + Flask 3 + gunicorn | Serve UI and JSON routes; **decided (D01)** |
| UI | React 19 + Vite 8, built to static files served by Flask | Team requirement: a JavaScript framework supported by Railway; **decided (D01)** |
| RAG orchestration | Plain Python modules (`app/`); Langflow custom component calls `/chat` | **Decided (D02)**; LangChain not used |
| Vector storage | Chroma 1.5.9 persistent, cosine | **Decided (D03)**; verified in workspace |
| Embeddings | `BAAI/bge-small-en-v1.5` (+ `hash` offline backend for CI) | **Decided (D04)**; bge path not yet executed (HF blocked in build workspace) |
| Generation | Groq `llama-3.1-8b-instant` via OpenAI-compatible API; fallback provider optional; `extractive` offline mode | **Decided (D05)**; free tier, 30 s timeout; live call not yet executed |
| Source corpus | 12 synthetic policies in md/txt/html/pdf + `data/manifest.json` | **Decided (D09)**; PDF citations use real pages, others use section anchors |
| Tests / CI | pytest + GitHub Actions | Offline checks plus separately configured live evaluation |

Pin and test actual package versions during M1. Keep model/provider access behind an adapter so retrieval and citation tests can run without network access or paid calls.

### Two processing flows

**Offline ingestion:** Corpus manifest → parse → clean → section-aware chunking → embeddings → persistent index + source metadata.

**Online answering:** Validate question → retrieve passages → assess evidence → generate constrained answer → validate source references → return answer and evidence.

Keep retrieval, generation and citation assembly separate. The model returns selected evidence IDs; the backend builds titles, snippets and URLs from trusted metadata. Never let the model invent a source URL.

### Proposed repository layout

```text
PROJECT_BLUEPRINT.md
README.md
design-and-evaluation.md
ai-tooling.md
requirements.txt
.env.example
.gitignore
app/
  routes.py
  config.py
  ingestion.py
  retrieval.py
  generation.py
  citations.py
  templates/index.html
  static/
data/
  policies/
  corpus-manifest.json
scripts/
  ingest.py
  evaluate.py
evaluation/
  questions.jsonl
  results/
tests/
.github/workflows/ci.yml
```

v0.2 actual layout differs slightly (spec layout): `app/{routes,config,parsing,chunking,embeddings,vectorstore,ingest,retriever,generator,guardrails,citations,rag,sources}.py`, `frontend/` (React), `data/manifest.json`, `eval/{questions.jsonl,run.py,results/}`, `langflow/`, `scripts/`, `tests/`. See README §3. Generated vector indexes should be ignored and reproducibly rebuilt; include the actual policy sources if permitted.

### Corpus and chunk metadata

Manifest fields: `document_id`, `title`, `filename`, `version`, `effective_date`, `category`, `page_count`, `sha256`, `provenance`, `permission_status`.

Chunk fields: `chunk_id`, `document_id`, `document_version`, `title`, `section`, `page_start`, `page_end`, `text`, `source_url`, `corpus_version`.

- Preserve page boundaries during extraction; do not infer page numbers from flattened text.
- Keep section headings with paragraphs. Remove repeated headers without deleting policy content.
- Suggested baseline: 500-token chunks, 75-token overlap, top-k 4. These are experiment settings, not proven optimum values.
- Calibrate any relevance threshold against answerable and unanswerable examples; vector similarity alone cannot guarantee answerability.
- Record embedding model/revision and chunk configuration in index metadata. Rebuild when source content or embedding settings change.
- Establish one current version per policy. Surface conflicting passages rather than silently choosing a convenient answer.

## 6. UI blueprint

**Style (P):** Light background, dark text, restrained blue/teal accent, readable type, generous spacing. Prioritize a useful answer and inspectable evidence.

| Area | Desktop behavior | Mobile behavior |
|---|---|---|
| Header | Name and “Answers from company policies, with sources” | Compact header |
| Policy navigation | Left sidebar, available policy list, New conversation | Collapsible menu |
| Main area | Welcome state, example questions, then messages | Full-width messages |
| Composer | Labeled question field and Send; Enter sends, Shift+Enter adds a line | Comfortable touch controls |
| Evidence | Numbered citations and expandable source cards below answers | Cards stacked below answers |

**Required UI states (P):** Welcome; retrieving/generating; supported answer; insufficient evidence; outside scope; invalid input; unavailable knowledge base; provider failure with retry.

- Display sources next to the answer they support, including title, section, page and exact excerpt.
- Clicking `[1]` focuses its source card; “View source” opens the matching policy page where the PDF viewer supports it.
- Do not show fabricated confidence percentages or imply every answer is guaranteed correct.
- Indicate that questions should be self-contained for this first release.
- Prevent duplicate sends while a request is pending. Preserve question text after errors.
- New conversation clears the local display; it does not erase server logs or an account history.
- Show accessible status messages and keyboard-visible focus. Render text safely rather than inserting model output as raw HTML.

**Illustrative answer only; not a verified company policy:**

> Submit annual leave through the HR portal and obtain manager approval before taking leave. [1]
>
> [1] Annual Leave Policy · Requesting Leave · page 2  
> “Employees must submit leave requests through the HR portal and obtain manager approval.”

### Wireframes to prepare

1. Welcome screen with suggested questions and policy navigation.
2. Answer screen with two citations and expanded evidence.
3. Insufficient-evidence and service-error states.
4. Mobile answer screen.

Annotate components with R05–R09 and R18–R20 where relevant. Figma is a proposed collaboration tool, not a verified requirement of this AI assignment.

## 7. Proposed API contract

Frozen in v0.2 and covered by `tests/test_api.py`. **v0.2 additions (D08):** responses also carry the spec's fields `refused`, `ref`, `doc_id`, `url`, plus `provider`, `truncated` and `retrieval` diagnostics; requests may use Langflow's `input_value` instead of `question` and an optional `session_id` (echoed). `/health` adds the spec's `index_loaded`, `chunks`, `version`. `/docs/<doc_id>` is an alias of `/sources/<doc_id>`. Non-PDF sources link to `#section-anchor` instead of `#page=N`.

### `POST /chat`

Request:

```json
{"question": "How do I request annual leave?"}
```

Successful response example using illustrative policy content:

```json
{
  "request_id": "req-example",
  "status": "answered",
  "answer": "Submit leave through the HR portal and obtain manager approval. [1]",
  "citations": [
    {
      "id": 1,
      "chunk_id": "leave-v1-p2-001",
      "document_id": "leave",
      "document_version": "1.0",
      "title": "Annual Leave Policy",
      "section": "Requesting Leave",
      "page_start": 2,
      "page_end": 2,
      "snippet": "Employees must submit leave requests through the HR portal and obtain manager approval.",
      "source_url": "/sources/leave#page=2"
    }
  ],
  "corpus_version": "v1",
  "latency_ms": 1200
}
```

`latency_ms` above is illustrative, not a measurement. It represents backend processing time; evaluation also measures client-observed request latency.

| HTTP | Response status | Meaning |
|---|---|---|
| 200 | `answered` | Evidence-backed answer; nonempty valid citations |
| 200 | `insufficient_evidence` | In-scope question cannot be answered; no invented answer or citations |
| 200 | `out_of_scope` | Request is unrelated to provided policies |
| 400 | `invalid_request` | Missing/empty/overlong question or malformed JSON |
| 503 | `knowledge_base_unavailable` | Index missing or unusable |
| 502 | `provider_error` | Generation provider fails |
| 504 | `provider_timeout` | Provider exceeds configured timeout |

Error schema: `{"request_id":"req-example","status":"provider_error","message":"The answer service is unavailable. Please retry."}`. Do not return secrets, provider payloads or stack traces.

**Input/output defaults (decided, D08):** Trim question; require 1–2,000 characters (blueprint value kept over the spec's 1,000; configurable); prompt for ≤150 words, `max_tokens` 300, hard cap 250 words verified after generation; provider timeout 30 seconds. Configure these values centrally. Verify the word cap after generation rather than assuming token limits enforce it. Shorten safely without leaving broken citations or changing meaning; otherwise return a controlled failure.

### Other routes

- `GET /`: chat UI.
- `GET /health`: HTTP 200 with `{"status":"ok","index_ready":true}` when app is running; `index_ready:false` when unindexed. This is a lightweight health response, not a live paid-model call. `/chat` returns 503 if its index is unavailable.
- `GET /sources/<document_id>` (P): serve only registered, permitted source PDFs. Unknown IDs return 404. The URL fragment `#page=2` is a viewer hint, not a server request parameter.

## 8. Answer safeguards and test cases

- Treat retrieved documents as evidence, never as instructions to override system behavior.
- Require material policy claims to have citations to provided chunks.
- Verify that citation IDs exist and snippets come from their stored source text. Structural checks do not prove semantic support; evaluate that separately.
- When evidence is missing, say so. Do not supplement policy answers with general model knowledge.
- For partially answerable questions, distinguish supported facts from missing information.
- Ask for clarification when a policy distinction makes the question ambiguous.
- Surface conflicting source versions or inconsistent policies; do not silently reconcile them.
- Test missing evidence, irrelevant questions, malicious instructions in questions/documents, invented source requests, model failures and malformed responses.

## 9. Development roadmap and task tracker

Ownership below is unassigned. Suggested split: Developer A handles corpus/RAG; Developer B handles UI/API/CI. Both review evaluation and documentation. These are collaboration roles, not assignments to named people.

| Milestone | Deliverable | Status | Owner | Exit gate |
|---|---|---|---|---|
| M1 | Verified scope and agreed interfaces | In review | Unassigned | Correct brief reviewed; decisions and API agreed |
| M2 | Policy corpus and evaluation dataset | Complete | Unassigned | Counts/provenance checked; expected evidence recorded |
| M3 | Reproducible ingestion | Complete | Unassigned | Rebuild works; metadata and sample text match sources |
| M4 | Retrieval baseline | In review | Unassigned | Expected passages retrieved for representative queries |
| M5 | Grounded generation and safeguards | In review | Unassigned | Supported/refusal/error paths pass checks |
| M6 | Complete UI/API user journey | Complete | Unassigned | Browser journey and API contract pass |
| M7 | Evaluation, reproducibility and CI | In progress | Unassigned | Actual metrics recorded; CI and fresh setup pass |
| M8 | Reviewed documentation and submission | In progress | Unassigned | Repository/demo/PDF access and checklist verified |

### M1 — Scope and technical agreement

- [ ] T01 Obtain correct AI brief; reconcile every R-tagged requirement and participant instruction. **Accept:** brief linked and discrepancies resolved. *Status:* In review — requirements text from team chat reconciled into R01–R16; official brief link still to attach.
- [ ] T02 Add repository URL, developer names, target date and task ownership. **Accept:** shared access and owners confirmed. *Status:* Not started — repository URL, owners and date pending.
- [x] T03 Select backend, orchestration, vector DB, embedding model and LLM. **Accept:** D01–D05 updated with exact choices and rationale. *Evidence:* D01–D05 decided (§11).
- [x] T04 Freeze API schema, UI wireframes and configuration defaults. **Accept:** both developers can implement against the same contract. *Evidence:* API contract frozen (§7, D08) and tested; UI built to §6 (screenshots in evidence log).
- [ ] T05 Establish environment and pin compatible dependencies. **Accept:** clean import/startup works on agreed Python version. *Status:* In review — runtime pins in `requirements.txt`; offline install/import verified on Python 3.11; torch/sentence-transformers install to verify on a networked machine.

### M2 — Corpus and expected answers

- [x] T06 Prepare coherent, permitted policies and manifest. **Accept:** reported document/page ranges met and page counts verified. *Evidence:* 12 docs, 4 formats, 32 pages (`data/manifest.json`, `tests/test_ingest.py::test_manifest_meets_corpus_requirements`).
- [x] T07 Review policy consistency, effective dates and source rights. **Accept:** no unresolved contradictions or unclear reuse permission. *Evidence:* Synthetic, team-owned; single version 1.0 per policy; facts kept non-overlapping except deliberate cross-references.
- [x] T08 Draft 20 evaluation questions with expected answer/refusal and evidence. **Accept:** set covers all policies plus boundary cases. *Evidence:* `eval/questions.jsonl` — 28 questions, all 12 policies + multi-doc, missing-evidence, out-of-scope, adversarial.

### M3 — Ingestion

- [x] T09 Parse PDFs preserving pages and headings. **Accept:** sampled extracted text matches originals. *Evidence:* `app/parsing.py`; PDF pages via bookmarks; tests `test_every_policy_parses_with_metadata`, `test_pdf_keeps_real_pages_and_removes_running_headers`.
- [x] T10 Chunk text and attach metadata. **Accept:** stable IDs, source links and page ranges verified. *Evidence:* `app/chunking.py`; `test_chunks_respect_size_overlap_and_ids`, `test_chunk_metadata_and_source_links`.
- [x] T11 Embed, persist and rebuild index. **Accept:** repeat build does not duplicate chunks; changed corpus triggers rebuild. *Evidence:* `python -m app.ingest`; `test_rebuild_is_idempotent`, `test_changed_file_is_detected`.

### M4 — Retrieval

- [x] T12 Implement configurable top-k retrieval. **Accept:** output includes passages, metadata and retrieval scores. *Evidence:* `app/retriever.py` returns passages, metadata, similarity and rerank scores.
- [x] T13 Inspect retrieval for a representative question subset. **Accept:** failures logged and baseline settings documented. *Evidence:* Offline baseline: retrieval failures logged in design-and-evaluation.md §6 (Q15, Q16).
- [ ] T14 Calibrate evidence checks and ambiguous/conflicting-source behavior. **Accept:** answerable and missing-evidence cases distinguishable without an arbitrary untested threshold. *Status:* In progress — threshold calibrated script added; hash backend checked (0.141 vs 0.130 separation); bge threshold must be calibrated on the first networked run.

### M5 — Generation and safeguards

- [ ] T15 Connect model adapter and evidence-only prompt. **Accept:** one complete question produces an evidence-supported answer. *Status:* In review — Groq adapter + evidence-only prompt implemented; tested with fakes and the extractive generator; first live Groq answer pending an API key.
- [x] T16 Assemble/validate citations and enforce output cap. **Accept:** unknown citations rejected; excerpts and links come from trusted metadata. *Evidence:* `app/citations.py`; tests for invalid markers, renumbering, verbatim snippets, metadata-only links, word cap.
- [x] T17 Handle unsupported, outside-scope, partial and conflicting answers. **Accept:** recorded boundary cases show expected behavior. *Evidence:* out_of_scope / insufficient_evidence paths tested; partial and conflicting handling via prompt rules (live check pending).
- [x] T18 Add input validation, provider timeouts, safe error handling and document-instruction protection. **Accept:** targeted failure cases pass. *Evidence:* 400/502/503/504 paths, delimiter stripping and timeouts tested in `tests/test_api.py`.

### M6 — UI and API

- [x] T19 Implement `/`, `/chat`, `/health` and source route. **Accept:** agreed API examples and error cases pass. *Evidence:* `/`, `/chat`, `/health`, `/sources/<id>` (+ `/docs`, `/api/policies`) — contract tests pass.
- [x] T20 Build responsive chat, policy menu, composer and evidence cards. **Accept:** end-to-end question → answer → source journey works. *Evidence:* React UI: sidebar policy list, composer, numbered citations focusing expandable source cards, View source links.
- [x] T21 Add all loading, refusal, empty-index and retry states. **Accept:** UI retains input on errors and prevents duplicate pending sends. *Evidence:* Pending, answered, refusal, error-with-retry states; input preserved after errors; send disabled while pending.
- [x] T22 Review mobile, keyboard use, escaped content and source access. **Accept:** issues corrected and review evidence linked. *Evidence:* Desktop + 390 px mobile screenshots reviewed; keyboard (Enter/Shift+Enter, Escape closes menu, visible focus); text rendered as text nodes; CSP on source pages.

### M7 — Evaluation and CI

- [x] T23 Add meaningful offline tests for ingestion, citations, endpoints and failure paths. **Accept:** tests run without live credentials. *Evidence:* 53 pytest tests + 3 Vitest tests, all offline.
- [ ] T24 Add GitHub Actions on push/PR with dependency installation and import/startup check. **Accept:** real workflow run passes. *Status:* In review — `.github/workflows/ci.yml` written and its steps run locally; needs a first green run on GitHub.
- [ ] T25 Run quality evaluation on frozen 15–30-question set. **Accept:** raw answers, evidence, human scores and failures saved. *Status:* In progress — offline baseline run saved (`eval/results/offline-baseline-hash-extractive/`); production run and human scores pending.
- [ ] T26 Measure 10–20 end-to-end request latencies; report p50/p95. **Accept:** raw timings, environment and calculation method saved. *Status:* In progress — offline latency recorded (p50 6.5 ms / p95 7.6 ms, no LLM); production and Railway latency pending.
- [ ] T27 Repeat setup from README in a fresh environment. **Accept:** developer can build corpus index and ask a live question. *Status:* Not started.

### M8 — Documentation and submission

- [ ] T28 Complete README, design/evaluation and AI-tooling documents. **Accept:** match actual code and measured results. *Status:* In progress — README, design-and-evaluation.md, ai-tooling.md drafted against the actual code; update with Run 2 results.
- [ ] T29 Review every requirement against implementation evidence. **Accept:** matrix has no unexplained unmet mandatory item.
- [ ] T30 Record required demo. **Accept:** correct brief's duration, participant and content conditions met.
- [ ] T31 Verify grader access and create submission PDF with repository/video links. **Accept:** links open using intended audience permissions.
- [ ] T32 Submit through the required dashboard process. **Accept:** submission confirmation recorded.

**Dependency order:** M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8. UI skeleton and CI setup may proceed after M1 while RAG work continues. Complete one live question-to-source path before polishing the full UI.

## 10. Evaluation plan and success targets

**Actual set (v0.2, D10):** 28 questions — 21 direct (every policy), 2 multi-document, 2 missing-evidence, 2 out-of-scope, 1 adversarial. Spec targets adopted: groundedness ≥90%, citation accuracy ≥90%, partial match ≥80%, refusal accuracy 100%, latency p50 <2.5 s / p95 <6 s. *(Original proposal: 20 questions — 10 direct policy questions, 4 requiring multiple passages, 2 ambiguous/partial questions, 2 missing-evidence questions and 2 outside-scope/adversarial questions.)* Distribute answerable questions across the whole corpus.

Each evaluation record contains: `question_id`, `question`, `category`, `expected_behavior`, `expected_facts`, `expected_document_ids`, `expected_sections/pages`, `actual_answer`, `returned_citations`, `groundedness_score`, `citation_judgments`, `behavior_pass`, `latency_ms`, `reviewer`, `notes`.

| Measure | Scoring method | Proposed target (P) |
|---|---|---|
| Groundedness | Supported material claims ÷ all material claims in answerable responses; mark empty/refusal outputs separately | ≥90%; also report answer completeness |
| Citation accuracy | Semantically supporting claim–citation links ÷ all emitted claim–citation links | ≥90%; uncited claims captured in groundedness review |
| Citation validity | Citation resolves to known source with matching snippet/location | 100% |
| Refusal/clarification behavior | Expected behavior achieved ÷ designated boundary cases | All selected cases pass |
| Latency | Client-observed complete POST `/chat` time, p50 and p95 | Provisional p95 ≤10 s; revise after provider choice |

Define material claims consistently and save reviewer judgments, numerators and denominators. If no claims or citations are emitted, report N/A rather than awarding a perfect score. Report answer coverage/completeness to prevent an assistant that refuses everything from appearing successful. Automated judging, if used, supplements documented human review.

**Latency protocol (P):** Measure 20 sequential, uncached requests on a warmed application/index. State whether the provider is warmed and record cold-start/index-build time separately. Save question IDs, timestamps, elapsed milliseconds, status and failures. Report successful-response percentiles plus failure count; do not hide failed requests. Use one documented percentile method (e.g., linear interpolation), model/configuration, host environment and corpus version.

| Run | Commit / corpus / model | Groundedness | Citation accuracy | Boundary cases | p50 / p95 | Evidence |
|---|---|---|---|---|---|---|
| Offline baseline (2026-10-01) | v0.2 / v1-2a44e4aa53 / hash + extractive | 100% (22/22, lexical proxy; trivial for extractive) | 72.7% (16/22) | 4/5 refusals | 6.5 ms / 7.6 ms | `eval/results/offline-baseline-hash-extractive/` |
| Production (bge + rerank + Groq) | Not run | Not measured | Not measured | Not measured | Not measured | None |

Changing chunking/retrieval/prompts after evaluation requires a new recorded run. Keep the original results rather than overwriting failures.

## 11. Decisions, blockers and handoff

### Decision register

| ID | Decision | Current proposal | Status / owner |
|---|---|---|---|
| D01 | Application structure | Single Flask service; React + Vite UI built to static files and served at `/` (team requirement: Flask + Railway-supported JS framework) | Decided 2026-10-01 / team request |
| D02 | Orchestration | Plain Python modules (product spec) instead of LangChain — fewer abstractions, easier to test and explain; Langflow supported through a custom component calling `/chat` | Decided 2026-10-01 / spec |
| D03 | Vector storage | Chroma 1.5.9 persistent client, cosine; rebuilt from scratch, not committed | Decided 2026-10-01 |
| D04 | Embedding model/revision | `BAAI/bge-small-en-v1.5` + cross-encoder `ms-marco-MiniLM-L-6-v2` re-ranker; deterministic `hash` backend for CI/offline | Decided 2026-10-01; revision pin pending first download |
| D05 | LLM provider/model and budget | Groq free tier, `llama-3.1-8b-instant`, temp 0, seed 42; OpenRouter as optional fallback; spend ceiling $0 (free tiers) | Decided 2026-10-01 |
| D06 | Hosting | Railway via Dockerfile + `railway.json` (models and index baked into image); local demo remains the fallback | Decided 2026-10-01 / team request |
| D07 | Conversation scope | Independent questions; no multi-turn context (stated in UI sidebar) | Decided 2026-10-01 |
| D08 | API contract details | Blueprint contract kept; spec fields added as aliases (`refused`, `ref`, `doc_id`, `url`, `/docs`, health `index_loaded/chunks/version`); `input_value` accepted for Langflow; question limit 2,000 chars | Decided 2026-10-01 |
| D09 | Corpus | 12 synthetic Acme Corp policies (5 md, 2 txt, 2 html, 3 pdf), 32 pages / 10,928 words; meets brief (30–120 pages), below spec's 50–70 estimate | Decided 2026-10-01 |
| D10 | Evaluation set | 28 questions (§10) | Decided 2026-10-01 |
| D11 | Chunking/retrieval baseline | Heading-first, 500-token windows, 75 overlap; top-k 8 → re-rank → top-n 4; threshold 0.35 (bge, to calibrate) / 0.12 (hash) | Decided 2026-10-01 |
| D12 | Manifest location | `data/manifest.json` (spec) instead of `data/corpus-manifest.json` | Decided 2026-10-01 |

When deciding, add date, decision-maker, rationale and affected requirement/task IDs. Avoid silent technology substitutions.

### Blocker register

| ID | Blocker / open question | Impact | Resolution / owner |
|---|---|---|---|
| B01 | Official brief link not yet attached (requirements text from team chat used) | Submission compliance not formally confirmed | Attach official brief / Mathew |
| B02 | Repository not yet pushed to GitHub | CI cannot run; grader access pending | Push and share with `quantic-grader` / Unassigned |
| B03 | Production models and Groq not executed yet (build workspace had no access to Hugging Face/Groq) | Run 2 metrics, bge threshold and live answers unverified | First networked run per README §1 + design doc §6 / Both developers |
| B04 | Deadline and availability unspecified | Cannot assign calendar dates | Agree target and capacity / Both developers |

### Developer handoff template

```markdown
Task ID:
Owner / reviewer:
Status:
Requirement IDs:
Files changed:
Behavior delivered:
Verification command and result:
PR / commit / artifact:
Blockers or limitations:
Next action:
Blueprint sections updated:
```

## 12. Evidence and progress log

| Task / requirement | PR or commit | Test / artifact / result | Reviewer | Date |
|---|---|---|---|---|
| Blueprint draft | Not in repository yet | This document; assignment-source mismatch recorded | Pending | 2026-10-01 |
| T06–T23 (v0.2 build) | Initial commit | `pytest`: 53 passed; `npm test`: 3 passed; `npm run build` ok; manifest rebuild deterministic | Pending | 2026-10-01 |
| T22 UI review | Initial commit | Headless Chromium screenshots at 1280×800 and 390×844 (welcome, answer with citation focus, refusal, mobile menu) | Pending | 2026-10-01 |
| T25/T26 offline baseline | Initial commit | `eval/results/offline-baseline-hash-extractive/summary.md` | Pending | 2026-10-01 |

| Date | Change | Progress | Next action |
|---|---|---|---|
| 2026-10-01 | Created v0.1 from supplied AI-project conversation; inspected attached florist PDF and flagged mismatch | 0/8 complete (0%); M1 in progress | Verify correct brief, agree stack and claim tasks |
| 2026-10-01 | v0.2: full implementation built from blueprint + product spec (Flask + React + Chroma + Groq adapter + Langflow component), corpus, tests, CI, Docker/Railway config, docs, offline evaluation | 3/8 complete (37.5%): M2, M3, M6 | Push to GitHub, first green CI, production evaluation run, Railway deploy |

## 13. Release and submission checklist

- [ ] Correct official brief reviewed; every mandatory requirement reconciled.
- [ ] Required document/page counts and permissions verified.
- [ ] Index builds from included sources with documented configuration.
- [ ] Live question → retrieval → answer → citation → source journey demonstrated.
- [ ] Unsupported/outside-scope and error paths verified.
- [ ] API behavior and responsive UI reviewed.
- [ ] Secrets excluded; `.env.example` contains placeholders only.
- [ ] GitHub Actions passes on the submission commit.
- [ ] Fresh setup and actual quality/latency results recorded.
- [ ] README and other documentation accurately describe the delivered app.
- [ ] AI-tooling record describes actual assistance, validation and corrections.
- [ ] Demo and participant instructions checked against the correct brief.
- [ ] Repository shared with the required grader account and video access verified.
- [ ] Submission PDF links are correct; submission confirmation saved.

**Definition of done:** A second developer can set up the submitted commit, rebuild its index, ask a policy question, inspect its real evidence, reproduce the documented checks and find the measured evaluation results. Mandatory requirements and submission access are verified; limitations are explicitly documented.

## 14. Next working session

1. Push the repository to GitHub, confirm a green CI run (T24) and share with `quantic-grader`.
2. On a networked machine: install, `python -m app.ingest` with bge, set `LLM_API_KEY`, calibrate the threshold (T14) and record evaluation Run 2 (T25, T26).
3. Complete human review columns in `review_sheet.csv`.
4. Deploy to Railway, record the URL and deployed latency in `deployed.md`.
5. Verify the Langflow component in Langflow; assign owners (T02); then record the demo (T30).

## 15. Change history

| Version | Date | Summary |
|---|---|---|
| 0.1 | 2026-10-01 | Initial development blueprint and tracker; all implementation completion claims remain unverified |
| 0.2 | 2026-10-01 | Stack and interfaces decided (D01–D12); implementation, tests and offline evaluation recorded; production-model checks still open |
