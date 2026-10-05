# AI Tooling

The brief allows AI coding assistance and requires that it be documented. This file records which tools were used, for what, how the output was checked, and what worked well or poorly. Team members should document their own AI-assisted work and validation steps here.

## Tools used

| Tool | Used by | Used for |
|---|---|---|
| Claude (Anthropic, Claude Opus 5.5) in the claude.ai agentic workspace | Munashe Sibanda | Generated the initial repository from the product spec, development planning material and requirements conversation: policy corpus, Flask RAG backend, React UI, tests, evaluation script, CI workflow, deployment configuration and first drafts of the documentation. |
| *(add any other AI tool the team used, e.g. ChatGPT or Copilot, and what for)* | | |

## How the AI assistant was used

1. **Inputs.** The assistant was given three documents: the requirements conversation (the brief as relayed in chat), development planning material (team process, API contract and UI states) and `Product Spec: PolicyPal RAG Assistant` (stack, corpus plan, metrics), plus the instruction to use Flask and a JavaScript frontend framework.
2. **Reconciling the sources.** Where the source materials disagreed, implementation decisions were made explicitly and then validated against the final working application (for example plain Python vs framework orchestration, `/sources` vs `/docs`, and input-length limits).
3. **Corpus.** The 12 Acme Corp policies were written by the assistant as original synthetic text with planted, non-overlapping facts for evaluation. They are fictional and owned by the team.
4. **Code and tests.** Code was written module by module and run in the workspace: the parsers were checked against every file, the pipeline was run end to end with the offline embedder and generator, the pytest suite (53 tests at the time) and 3 frontend tests were run, the UI was screenshotted at desktop and mobile widths in headless Chromium, and the evaluation script was run against a live gunicorn server.
5. **Evaluation.** The assistant ran the offline baseline evaluation and reported the actual numbers, including the metrics that missed their targets.

## What worked well

- **Turning specs into a test-backed skeleton quickly.** The API contract tables in the blueprint translated directly into contract tests (`tests/test_api.py`), which then caught real bugs.
- **Offline fallbacks.** Designing a hash embedder and an extractive generator let the whole pipeline, CI and evaluation run without model downloads or API keys.
- **Consistency checks.** Asking for manifest hashes, stable chunk IDs and verbatim-snippet checks produced guardrails that are cheap to test.

## What worked poorly / corrections made

| Problem | How it was found | Fix |
|---|---|---|
| Rebuilding the index deleted the Chroma directory, but Chroma caches clients per path within a process, so the second build in the same process failed with "Collection already exists". | `test_rebuild_is_idempotent` failed. | Delete the collection through the client instead of removing the folder. |
| First attempt to install `vite@7` with the newest `@vitejs/plugin-react` failed on a peer-dependency conflict. | `npm install` error. | Checked peer requirements with `npm view` and moved to Vite 8 + plugin-react 6 + Vitest 5. |
| The extractive generator first appended a weak second sentence to good answers (e.g. a PTO payout sentence after the carry-over answer). | Manual review of smoke-test answers. | Only add further sentences that score at least 80% of the best sentence. |
| Shell command `pkill -f gunicorn` matched and killed the assistant's own shell. | Command exited with code 144. | Used `pgrep`/`kill` on the gunicorn binary path instead. |
| The workspace could not reach Hugging Face, Groq or the PyTorch index, so the production embedder, re-ranker and LLM client could not be executed, and no Docker daemon was available. | Network checks at the start of the session. | Implemented them behind the same interfaces as the tested offline components, documented them as unverified, and listed the first live run as an open task. **These paths need human verification.** |
| The evaluation questions are also used to suggest a threshold, which risks overfitting. | Noted while writing `calibrate_threshold.py`. | Left the hash threshold at its default and printed a warning in the script. |

| A Windows-only bug: Git can convert line endings to CRLF on checkout, which changed the SHA-256 of every text policy, so a reviewer cloning on Windows could fail the manifest check. | Found by Claude during the pre-submission review. | Text files are hashed with LF line endings, and `.gitattributes` keeps `data/policies/` byte-identical; a test covers it. |
| The README had lost its Markdown formatting (headings, code blocks and tables were pasted as plain text), and the main `Dockerfile` referenced a deleted script. | Pre-submission review. | README restored with proper Markdown; `scripts/download_models.py` restored for the ONNX backend. |

## Human validation and changes made by the team

The AI-generated starting point was not used as-is. The team ran, checked and changed it:

- **Embeddings.** The planned `sentence-transformers` backend could not load on the Windows development machine (application control blocked PyTorch's `c10.dll`). Rather than weaken the security policy, the team switched the production configuration to Chroma's ONNX MiniLM model, which needs no PyTorch.
- **LLM.** Groq `openai/gpt-oss-20b` was selected after testing; the extractive fallback was wired in so provider failures still return a cited answer, and was verified by deliberately using an invalid API key.
- **Evaluation.** The first ONNX + Groq run hit Groq rate limits (14 of 28 answers came from the fallback). The team added `--delay-s` to the evaluator and re-ran until all 28 answers came from Groq. The six answers the lexical proxy marked as ungrounded were checked by hand against their cited passages (`review_sheet.csv`).
- **Deployment.** The team deployed to Render and verified `/health` and cited answers on the public URL.

## Second iteration: policy updates (Claude)

To make the knowledge base maintainable, and easy for a reviewer to test, Claude added runtime policy management:

- an `/admin` page and `/api/admin` endpoints (protected by `ADMIN_TOKEN`) to add, replace, remove and reset policies;
- automatic metadata for files without headers and automatic version bumps on replacement;
- incremental re-embedding, so one update re-embeds only the changed policy;
- a read/write lock so chat requests never see a half-built index;
- sample update files in `examples/policy-updates/`, 13 new tests, and a CI step that uploads a policy to the running server and asks about it.

Claude ran the full test suite (69 tests), the frontend build, and a browser walkthrough of the admin page (upload, answer change, reset) against a local server using the offline embedder. The ONNX model download was not reachable from its workspace, so **the team verified the same flow with the ONNX + Groq configuration locally and on Render.**

## What we learned

- AI assistance was fastest for well-specified, testable pieces (API contract, parsers, citation mapping) and for writing tests that then caught real bugs.
- Environment-specific problems (Windows DLL policy, provider rate limits, free-tier memory) only appeared when running the code on our own machines and host; they needed human diagnosis and design decisions.
- Automated metrics needed human judgement: the lexical groundedness proxy under-reported paraphrased but correct answers.
