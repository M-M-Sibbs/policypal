# PolicyPal repair handoff — 2026-10-22

Branch: `fix/rag-generation-and-citations`. Base commit: `bf0654b`. The user subsequently authorized committing these changes on the repair branch. Nothing was pushed, merged or deployed. The local `.env`, committed policies, hosted corpus and Render settings were not changed.

## Root causes and changes

Citation cleanup previously retained unsupported claims after deleting invalid markers. Strict sentence-level format validation now precedes cleanup/capping, followed by one correction attempt containing the rejected answer. Sentence splitting keeps trailing markers with their claim. Snippet ranking handles approval/approve variants and numeric bands; excerpts preserve list/table context and evidence for compound/repeated claims. These are structural and lexical protections, not semantic proof.

Provider errors previously disappeared into fallback. The API/UI now identify LLM, offline demo, degraded extractive and unavailable modes, with strict requests, safe error categories and request-isolated metadata. Health distinguishes configuration from timestamped process-local observations without provider calls. The local reasoning-token exhaustion finding has a safe recorded probe; the hosted provider cause remains unknown.

Evaluation now reports incorrect refusals, relevance, format validity, displayed evidence completeness, per-marker lexical support, real provider coverage/failures and provenance. Human review remains blank. Vite 8.3.2 was upgraded compatibly to 8.3.3. The high finding was [GHSA-587h-7wmj-h5pm](https://github.com/vitejs/launch-editor/security/advisories/GHSA-587h-7wmj-h5pm), affecting Windows development editor middleware. The deployed Flask static build does not expose that middleware. Audit also listed five related/lower-severity advisories under Vite; the patched audit reports none.

## Changed files

- Runtime: `.env.example`, `app/citations.py`, `app/config.py`, `app/generator.py`, `app/rag.py`, `app/routes.py`.
- UI/dependencies: `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/components/Messages.jsx`, `frontend/src/styles.css`.
- Evaluation: `eval/run.py`, `eval/questions.jsonl`, new local/hosted run folders dated 20261022 under `eval/results/` (including failed iterations).
- Tests: `tests/test_citation_regressions.py`, `tests/test_provider_modes.py`, `tests/test_evaluation.py`.
- Documentation: `README.md`, `design-and-evaluation.md`, `ai-tooling.md`, `PROJECT_BLUEPRINT.md`, `requirements-compliance.md`, `docs/render-checklist.md`, this file.

## Verification and limitations

Baseline: 73 existing backend tests passed after installing missing pytest 9.1.1 into the existing `.venv`. Added regressions were observed failing before fixes. Final verification: 116 backend tests passed. `git diff --check` passed.

Frontend: clean `npm ci`, 3 unit tests and Vite production build passed; `npm audit` reports 0 vulnerabilities. `scripts/verify_project.py` passed (12 documents, 32 manifest pages). No remote CI run is claimed. Independent review agent could not run because of an account usage limit; main-session review and verification were performed.

Local HTTP verification used a separate server at `http://127.0.0.1:5012`, with process-only `MAX_TOKENS=1200`, `LLM_REASONING_EFFORT=low` and `PRELOAD_PIPELINE=0`. The user's port 5001 service was not modified. The temporary port 5012 server was stopped after verification. See [local run](../eval/results/local-handoff-20261022/summary.md): all eight required questions passed automated/strict checks, with six cited answers and two expected refusals. Seven requests used Groq; prompt injection was refused before generation. The separate displayed lexical-support proxy passed 4/6 answers; two paraphrase/wording flags remain for human review. This is not a human semantic score. Cited source routes for POL-02/03/06/07/08 all returned 200. Answers and displayed snippet strings were inspected; no browser visual walkthrough or named human semantic review was performed. A final request-state isolation fix followed this run and was covered by tests.

See [hosted observation](../eval/results/hosted-observation-20261022/summary.md): all eight labels were extractive on the old deployment. Expense was incorrectly refused; dogs and torrent received irrelevant answers. Configuration/underlying provider failure cannot be inferred from the old response schema. No policies were uploaded/reset. Follow the [Render checklist](render-checklist.md); Render logs/account access and human semantic review remain outstanding.

The full 28-question live benchmark was not rerun. Earlier failed local runs are retained and labelled; the eight-case result is not a general accuracy or performance guarantee. Historical 100% semantic/compliance claims were qualified or withdrawn.

## PowerShell verification

Run from the repository. These process-only settings do not overwrite `.env`. Port 5012 must be free; stop your verification server with Ctrl+C when finished.

```powershell
Set-Location C:\Users\kyrie\Projects\policypal
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
$env:PRELOAD_PIPELINE = '0'
.\.venv\Scripts\python.exe -m pytest -ra
.\.venv\Scripts\python.exe scripts/verify_project.py
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend audit --audit-level=high
git diff --check

# Terminal 1: start the verification server.
$env:MAX_TOKENS = '1200'
$env:LLM_REASONING_EFFORT = 'low'
.\.venv\Scripts\python.exe -m flask --app app run --host 127.0.0.1 --port 5012
```

In a second PowerShell terminal:

```powershell
Set-Location C:\Users\kyrie\Projects\policypal
$env:PRELOAD_PIPELINE = '0'
$runName = 'local-review-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
.\.venv\Scripts\python.exe -m eval.run --url http://127.0.0.1:5012 --name $runName --strict-llm --evidence-index storage/chroma --ids Q01,Q03,Q12,Q14,Q15,Q22,Q24,Q28 --latency-n 8 --delay-s 5
$LASTEXITCODE  # 0 = automated checks pass; 2 = inspect failed checks. Human review still required.
# Omit --ids to run all 28 questions.
```

## Commit and push when you are ready

These commands were not executed. Review the staged diff before committing. Push only this repair branch; do not merge/deploy as part of these commands.

```powershell
Set-Location C:\Users\kyrie\Projects\policypal
git branch --show-current  # must be fix/rag-generation-and-citations
git status --short
git diff --check
git add -- .env.example app/citations.py app/config.py app/generator.py app/rag.py app/routes.py frontend/package.json frontend/package-lock.json frontend/src/components/Messages.jsx frontend/src/styles.css eval/run.py eval/questions.jsonl tests/test_citation_regressions.py tests/test_provider_modes.py tests/test_evaluation.py README.md design-and-evaluation.md ai-tooling.md PROJECT_BLUEPRINT.md requirements-compliance.md docs/render-checklist.md docs/repair-handoff.md
git add -- eval/results/local-repair-20261022 eval/results/local-verified-20261022 eval/results/local-final-20261022 eval/results/local-handoff-20261022 eval/results/hosted-observation-20261022
git diff --cached --stat
git diff --cached
git commit -m "Fix citation validation, evidence snippets and provider visibility"
git push -u origin fix/rag-generation-and-citations
```
