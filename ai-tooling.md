# AI Tooling

The brief allows AI coding assistance and requires that it be documented. This file records which tools were used, for what, how the output was checked, and what worked well or poorly. Team members should add their own entries as they continue the work (rule 8 of `PROJECT_BLUEPRINT.md`).

## Tools used

| Tool | Used by | Used for |
|---|---|---|
| Claude (Anthropic, Claude Opus 5.5) in the claude.ai agentic workspace | Munashe Sibanda | Generated the initial repository from the product spec, the development blueprint and the requirements conversation: policy corpus, Flask RAG backend, React UI, tests, evaluation script, CI workflow, Dockerfile/Railway config and first drafts of the documentation. |
| *(add others, e.g. GitHub Copilot, ChatGPT, Cursor)* | | |

## How the AI assistant was used

1. **Inputs.** The assistant was given three documents: the requirements conversation (the brief as relayed in chat), `Company_Policy_Assistant_Blueprint 2.md` (team process, API contract, UI states) and `Product Spec: PolicyPal RAG Assistant` (stack, corpus plan, metrics), plus Langflow's Chat Input component and the instruction to use Flask and a Railway-supported JavaScript framework.
2. **Reconciling the sources.** Where the documents disagreed, the assistant chose one option and recorded it as a decision in `PROJECT_BLUEPRINT.md` instead of silently picking (e.g. plain Python vs LangChain, `/sources` vs `/docs`, 2,000 vs 1,000 character input limit, Render vs Railway).
3. **Corpus.** The 12 Acme Corp policies were written by the assistant as original synthetic text with planted, non-overlapping facts for evaluation. They are fictional and owned by the team.
4. **Code and tests.** Code was written module by module and run in the workspace: the parsers were checked against every file, the pipeline was run end to end with the offline embedder and generator, the 53-test pytest suite and 3 frontend tests were run, the UI was screenshotted at desktop and mobile widths in headless Chromium, and the evaluation script was run against a live gunicorn server.
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

## Human review still required

- Run the production configuration (bge + re-ranker + Groq) and record Run 2 in `design-and-evaluation.md`.
- Complete the human columns in `eval/results/*/review_sheet.csv`.
- Read every policy for tone and internal consistency before the demo.
- Check the Langflow component in a real Langflow install (written against the `lfx` component API but not executed).
- Review that the Railway deployment fits the chosen plan's memory.
