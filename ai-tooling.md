# AI Tooling

The brief encourages AI coding tools and asks us to describe which ones we used, how we used them, and what worked well or poorly. This file is that record. A longer explanation of the planning documents and the RAG algorithm is in [docs/project-inputs.md](docs/project-inputs.md).

## 1. Tools used

| Tool | Used by | Used for |
|---|---|---|
| **Claude** (Anthropic, model Claude Opus 5.5) in claude.ai's agentic workspace (a cloud Linux sandbox where the assistant can write files, run Python/Node, run tests and drive a headless browser) | Munashe Sibanda | Generated the first complete repository from our planning documents (1 Oct 2026); reviewed the submitted repository against the brief and rubric, fixed defects and added runtime policy updates (5 Oct); wrote the submission documents (6 Oct); guided local setup, GitHub and Render deployment step by step. |
| *(add any other AI tool the team used, e.g. ChatGPT, Copilot or Cursor, and what for)* | | |

## 2. What we gave the AI, and how each input was used

We did not ask for "a chatbot". We gave Claude five inputs that already contained most of the design decisions, and asked it to build the project so that it followed them.

| # | Input | Author | What it contained | How Claude used it |
|---|---|---|---|---|
| 1 | **Requirements conversation** (`attachment.txt`, team chat of 1 Oct 2026) | Tapiwa Mathew Muwomo | The project brief as relayed in chat (corpus size, ingestion, RAG answers with citations, `/`, `/chat`, `/health`, reproducibility, CI, evaluation metrics, documentation, demo), plus a proposed stack (Flask, LangChain, Chroma, local embeddings, API LLM, HTML/CSS/JS, GitHub Actions) and the answering flow: *question → retrieve policy sections → LLM answers from that evidence → show answer with citations and snippets; handle questions the policies can't answer; evaluate groundedness, citation accuracy and latency.* | Became the requirements checklist and the shape of the online pipeline (the "algorithm", §3). Every listed requirement maps to code, tests or documents (see [requirements-compliance.md](requirements-compliance.md)). |
| 2 | **Development blueprint** (`Company_Policy_Assistant_Blueprint 2.md`) | Mathew Muwomo (with Munashe Sibanda) | Requirement IDs R01–R21, a frozen API contract (statuses `answered`, `insufficient_evidence`, `out_of_scope`, 400/502/503/504 errors), chunk and manifest metadata fields, UI layout and required states, safeguards (citations built from trusted metadata, documents treated as data, length cap verified after generation), evaluation record fields, milestones M1–M8. | The API contract was implemented as written and turned into contract tests (`tests/test_api.py`). Its rule that *the model returns evidence IDs and the backend builds titles, snippets and URLs* became `app/citations.py`. The UI states (welcome, loading, answer, insufficient evidence, out of scope, invalid input, unavailable, provider error with retry) are all in the React app. Claude kept the blueprint updated as a tracker during the first build. |
| 3 | **Product spec** (`Product Spec: PolicyPal RAG Assistant`, 11 pages) | Munashe Sibanda | Goal of a rubric score of 5; the 12-policy corpus plan (IDs, formats, page targets, facts to plant); functional requirements FR-1 to FR-16; the stack (plain Python orchestration, bge-small embeddings, Chroma, cross-encoder re-ranker, Groq LLM, Render); the evaluation plan and metric definitions; CI/CD with a Render deploy hook; risks. | The corpus was written to the spec's table (POL-01 to POL-12 in the specified formats, with planted, non-overlapping facts and deliberate cross-references). FR-1 to FR-16 map one-to-one to modules and tests. The evaluation set and metric definitions follow the spec, and its "plain Python instead of LangChain" decision settled the conflict with input 1. |
| 4 | **Langflow Chat Input component** (Python source pasted into the request) | Team (from Langflow) | The source of Langflow's `ChatInput` component: its inputs (`input_value`, `session_id`, `sender`, `files`, `should_store_message`) and its output, a Langflow `Message`. | See §4. Claude made `POST /chat` accept Langflow's message fields and wrote a Langflow custom component (`langflow/policypal_component.py`) so a Langflow flow can use PolicyPal. |
| 5 | **Instruction**: *"must be written in Flask and a JavaScript framework supported by Railway; the blueprint must be followed"* | Munashe Sibanda | Technology constraint. | Flask backend + React (Vite) frontend compiled to static files served by Flask: one service, deployable on Railway or Render. The spec had suggested plain HTML/JS; the instruction took precedence. |

Later in the project we also gave Claude: the official brief (`project_ai.pdf`), the repository as submitted (`company-policy-rag-main.zip`), the live Render URL, and screenshots and terminal output from our own machines. These were used to check the work against the rubric and to diagnose setup problems (see §6).

### Where the inputs disagreed

Claude was asked not to switch technologies silently. Each conflict was resolved explicitly and recorded:

| Topic | Inputs said | Final choice and reason |
|---|---|---|
| Orchestration | Chat: LangChain. Spec: plain Python ("LangChain optional"). Brief: LangChain recommended but optional. | Plain Python modules, following the spec: each RAG step is visible and unit-testable. |
| Frontend | Chat/spec: HTML/CSS/JS. Instruction: a JS framework. | React + Vite, built and served by Flask. |
| Question length limit | Blueprint: 2,000 characters. Spec: 1,000. | 2,000 (blueprint), configurable with `MAX_QUESTION_CHARS`. |
| Source links | Blueprint: `/sources/<id>`. Spec: `/docs/<id>`. | Both routes exist. |
| Embeddings | Spec: bge-small via sentence-transformers (PyTorch). | Team changed to ONNX MiniLM after PyTorch was blocked on our Windows machine (§5). |
| Hosting | Instruction: Railway. Spec: Render. | Both configs written; deployed on Render. |
| Policy editing | Spec non-goal: "editing or uploading policies through the UI". | Added later at the team's request, so the grader can test updates (§6). |

## 3. The algorithm we specified, and how it was implemented

Input 1 described the flow informally; the spec (FR-5 to FR-11) made it precise. Claude implemented it as this algorithm (`app/rag.py`):

```text
answer(question):
    validate question (1–2,000 chars, text only)                      # blueprint, FR-14
    candidates = top 8 chunks by cosine similarity in Chroma          # FR-5
    if best similarity < SCORE_THRESHOLD:                             # FR-6
        return "I can only answer about our policies."  (no LLM call)
    evidence = top 4 candidates (re-ranked if RERANK=1)               # FR-5
    prompt = rules + numbered evidence [1]..[4] + question            # FR-7, FR-12
    repeat at most twice:                                             # FR-11
        text = LLM(prompt)          (temperature 0, ≤300 tokens)      # FR-10
        if text says INSUFFICIENT_EVIDENCE: return polite refusal     # FR-9
        cap answer at 250 words on sentence boundaries                # blueprint
        citations = map [n] markers to stored chunk metadata;         # FR-8
                    drop unknown markers; snippet = exact passage text
        if citations: return answer + citations
    return refusal (no answer could be cited)
```

The offline half (`app/ingest.py`) parses md/txt/html/pdf, cleans them, chunks by headings and then 500-token windows with 75-token overlap, embeds the chunks and stores them in Chroma (FR-1 to FR-4).

## 4. Langflow and LangChain: what actually happened

To be precise about this, since it is easy to misdescribe:

- **What we provided** was the source code of Langflow's *Chat Input* component. It is a Langflow UI building block that turns typed text into a `Message`; it is not a complete flow, and it contains no retrieval logic and no LangChain chain.
- **What Claude did with it:**
  1. Read the component's interface and made the API compatible with it: `POST /chat` accepts Langflow's `input_value` field as well as `question`, accepts and echoes `session_id`, and rejects `files` with HTTP 400 (PolicyPal answers text questions only).
  2. Wrote a **Langflow custom component**, `langflow/policypal_component.py`, which takes the Chat Input `Message`, calls `POST /chat`, and returns the cited answer as a `Message` (plus the citations as Langflow `Data`). A Langflow flow *Chat Input → PolicyPal RAG → Chat Output* therefore runs on exactly the same pipeline, guardrails and citations as the web app.
  3. Added offline tests (`tests/test_langflow_component.py`) that run the component with stand-ins for the Langflow classes.
- **What we did not do:** we did not export a pipeline from Langflow, and no LangChain code was generated and then translated. The RAG pipeline was written directly in Python, following the product spec's decision. LangChain is not a dependency.
- **Status:** the component is tested offline but has not yet been run inside a full Langflow installation.

## 5. What the team did (human work and validation)

AI output was a starting point; the team ran, checked and changed it:

- **Embeddings.** The spec's `sentence-transformers` backend could not load on our Windows machine, because application control blocked PyTorch's `c10.dll`. Instead of weakening the security policy, the team switched production embeddings to Chroma's ONNX MiniLM model (`EMBED_BACKEND=onnx`), which needs no PyTorch.
- **LLM.** We selected Groq `openai/gpt-oss-20b` after testing. We kept an extractive fallback so provider failures still return a cited answer, and verified it by deliberately using an invalid API key.
- **Evaluation.** The first ONNX + Groq run hit Groq's rate limits (14 of 28 answers came from the fallback). We added `--delay-s` to the evaluator and re-ran until all 28 answers came from Groq. The answers the automatic lexical check flagged were reviewed by hand against their cited passages (`eval/results/onnx-groq-final/review_sheet.csv`).
- **Deployment.** We deployed to Render, set secrets as environment variables, and checked `/health` and cited answers on the public URL.

## 6. Second and third sessions with Claude (5–6 October)

**Review against the rubric.** Claude compared the submitted repository and live site with the official brief and rubric, then fixed what it found:

- The README had lost its Markdown formatting (pasted as plain text), so on GitHub it showed as one block of text.
- Windows checkouts change line endings, which changed every text policy's SHA-256 and would make the corpus check fail for a reviewer cloning on Windows. Hashes now ignore line endings, and `.gitattributes` keeps policies byte-identical.
- The main `Dockerfile` referenced a deleted script.
- The Render image could build its index with a different embedding backend from the one the running app used (`index_ready: false`). The build now takes its settings from Render's environment and rebuilds at start-up on mismatch.

**Runtime policy updates** (requested so a grader can test updates): a token-protected `/admin` page and `/api/admin` API to add, replace, remove and reset policies, automatic metadata and version bumps, incremental re-embedding (only changed chunks), a read/write lock so chat never reads a half-built index, sample update files, and 13 tests plus a CI step that uploads a policy to the running server.

**Documentation:** this file, [requirements-compliance.md](requirements-compliance.md), [docs/project-inputs.md](docs/project-inputs.md), [docs/github-actions.md](docs/github-actions.md), the submission PDF generator, and the restored Langflow component.

How Claude verified its work: it ran the full test suite (73 backend tests), the frontend tests and build, a simulated Windows clone, the CI steps against a local gunicorn server, and a headless-browser walkthrough of the admin page. Its workspace could not reach Hugging Face, Groq or Render's build system, so the ONNX + Groq path on Render was verified by the team.

## 7. What worked well

- **Detailed specs in, testable code out.** Because the blueprint and spec already fixed the API contract, metadata and metrics, the generated code could be checked against them. The contract tables became tests that then caught real bugs.
- **Offline modes.** A hash embedder and an extractive generator let the pipeline, CI and tests run with no API key or model download.
- **Review passes.** Asking the assistant to audit the finished repository against the rubric found problems we had missed (README formatting, Windows hashes, a build mismatch).
- **Step-by-step guidance** for environment problems (Python version, Command Prompt vs PowerShell syntax, virtual environment activation, Render settings).

## 8. What worked poorly / corrections

| Problem | How it was found | Fix |
|---|---|---|
| The assistant's workspace could not reach Hugging Face, Groq or PyTorch downloads, so the first build could not run the real embedder or LLM. | Network checks at the start. | Real components built behind the same interfaces as tested offline ones and marked unverified; the team then ran them locally. |
| PyTorch blocked on Windows by application control. | Local run by the team. | Switched to ONNX embeddings (§5). |
| Groq free-tier rate limits during evaluation. | Mixed providers in the first results. | `--delay-s` throttling and re-run. |
| Index rebuild in the same process failed ("collection already exists"). | A unit test. | Delete the collection through the Chroma client. |
| A dependency conflict between Vite and its React plugin. | `npm install` error. | Upgraded to compatible versions. |
| Instructions written for PowerShell were run in Command Prompt (`$env:` syntax), and updates were extracted from the wrong zip. | Terminal output shared with the assistant. | Re-issued commands for Command Prompt; added checks (`findstr`, `dir`) before each step. |
| Generated documents can drift from the code (e.g. old model names, stale test counts). | Review pass. | Documents rechecked against the repository before submission. |

## 9. What we learned

- AI assistance was fastest where the target was precisely specified and testable; most of our time went into writing the spec and blueprint first.
- Environment-specific problems (Windows security policy, provider rate limits, free-tier memory, build vs runtime settings) only appeared on real machines and needed human diagnosis and decisions.
- Automated metrics need human judgement: the lexical groundedness proxy under-counted correct paraphrased answers.
- Every AI claim had to be checked. Statements in this repository about tests and results refer to runs we can reproduce from the README.
