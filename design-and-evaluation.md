# PolicyPal design and evaluation

Updated 2026-10-22. The Flask/React, Chroma and ONNX architecture is unchanged. Retrieval, generation, citation assembly and HTTP routes remain separate modules. The committed synthetic corpus contains 12 policies, 203 indexed chunks and corpus version `v1-2a44e4aa53`; runtime uploads can change those values.

## Repair findings

- Citation markers after a full stop were not kept with their sentence. The resulting combined claims could select the wrong rule. Lexical scoring also penalised numeric ranges and favoured short, generic list introductions. The saved Q12 expense card in `onnx-groq-final` quoted CFO/CEO approvals; Q15 omitted the torrent item.
- The pipeline accepted any answer containing at least one surviving valid marker. Removing `[99]` left an unsupported bonus statement in an accepted answer. Validation now rejects unknown/malformed markers and uncited sentences before truncation or cleanup. One correction attempt supplies the previous answer and explicit citation feedback; failure returns a refusal.
- Snippets now use each marker's own sentences/clauses, preserve list introductions and table headers, and include evidence for repeated markers. Omitted intervening text is visibly separated by an ellipsis. Individual long excerpts can be shortened and flagged; cards may exceed 300 characters to retain multiple facts/context. Exact excerpt provenance is distinct from semantic support.
- Provider failures were swallowed by extractive fallback, and mutable provider labels could leak between concurrent requests. Request-local generation metadata and timestamped process-local observations replace that ambiguity. Error logs contain only provider identifier, category and HTTP status, never keys, headers, raw exceptions or response bodies.
- A local controlled Q22 retry exhausted all 300 completion tokens in reasoning and returned empty content (`finish_reason=length`). With `MAX_TOKENS=1200` and `LLM_REASONING_EFFORT=low`, it completed with 64 tokens. See [safe probe metadata](eval/results/local-repair-20261022/provider-diagnostic.json). This diagnoses that local failure only. Groq documents the reasoning controls in its [reasoning guide](https://console.groq.com/docs/reasoning).

## Runtime contract

`status=answered` remains compatible with existing clients. `generation.mode` distinguishes `llm`, `offline_demo`, `degraded`, `not_attempted` and `unavailable`. An evidence refusal can still carry `llm` when the provider generated it; a retrieval refusal has no provider and `not_attempted`. Extractive text is a lexical demo with known relevance limitations, not a guarantee of an accurate answer.

`LLM_PROVIDER=extractive` explicitly selects the demo. `ALLOW_EXTRACTIVE_FALLBACK=0`, `REQUIRE_LLM=1`, or a request containing boolean `require_llm: true` prevents silent extractive substitution. If providers fail and fallback cannot answer, return 502/504, not a policy refusal. Safe categories include configuration, authentication, rate_limit, model_rejection, timeout, connection, upstream, malformed_response and token_limit. HTTP 400/404/422 are broad request/model rejection categories; they do not prove a model was retired.

`/health` reports configured provider separately from last observed provider availability. It never calls a paid model or loads an unloaded pipeline. Observations are per process, may be stale, reset on restart and can differ between workers. They establish neither future availability nor semantic accuracy.

The prompt targets 150 words and the backend caps answers at 250 words. Reasoning-model token budgets include reasoning; the repair run uses 1200 tokens and low effort through process-only overrides. Defaults/older Render environments may still contain 300. Neither the local `.env` nor Render settings were changed. `render.yaml` is deliberately unchanged.

## Evaluation method and limitations

`python -m eval.run` evaluates the 28-question set, or a subset with `--ids`. It writes answers/cards, configuration reported by the server, corpus version, evaluator commit/dirty state and tracked diff hash, question-set hash, provider counts/failures, timings and an empty human-review sheet. The evaluator commit is not asserted to be the deployed revision; an unreported server revision is `unknown`.

Checks are explicitly automated proxies:

- Citation-format validity checks every sentence, marker range, duplicate card IDs and marker/card correspondence.
- Per-sentence lexical support checks only that sentence's assigned citations, separately for displayed snippets and available full passages. Negation, paraphrases and erroneous inferences can fool lexical overlap.
- Required fact groups for the repair questions catch missing approval roles, amount bands and the torrent item. The other legacy questions retain partial keyword proxies. Correct document IDs alone do not establish support.
- Incorrect refusals and unrelated answers fail behavior checks. Displayed evidence omissions and known non-verbatim excerpts fail the combined automated check. Lexical-support results remain separate review flags because paraphrases can fail them.
- `--strict-llm` requests strict service behavior and independently fails degraded, demo or unknown coverage. Expected retrieval refusals can pass without an LLM call. Old servers that ignore the request flag do not receive assumed LLM credit.
- `--evidence-index` is optional and used only when its corpus and index configuration match server-reported values. Otherwise provenance is unknown. Hosted responses are never validated against a silently assumed local corpus. Corpus changes during a run require a new run and review.
- Optional LLM judge output is labelled separately. Invalid/failed verdicts remain unknown. No judge result is a human review.

Latency is sequential client wall-clock time after one separately recorded warm-up. Delay between requests is excluded. HTTP-200 and observed-LLM latency are reported separately, with counts. Eight-request repair checks are diagnostic samples, not a new full performance benchmark.

## Recorded runs

Historical folders `offline-baseline-hash-extractive`, `onnx-groq-final` and `render-latency` are retained unchanged as historical artifacts. Earlier 100% citation/human-grounding and compliance claims are withdrawn as evidence for this repair: document matching missed incorrect displayed snippets, and historical reviews have not been independently repeated here.

The new local runs preserve failed iterations rather than overwriting them:

- `local-repair-20261022`: 300-token configuration; four provider failures.
- `local-verified-20261022`: 1200/low; three incorrect refusals from paragraph-end citations.
- `local-final-20261022`: intermediate prompt; still rejected uncited sentences.
- `local-handoff-20261022`: all eight automated/strict checks passed: six answers, the expected dogs refusal generated by Groq, and a prompt-injection refusal before generation. Seven requests used Groq; one did not call a model. Six answered responses passed citation-format, verbatim-excerpt and required-evidence checks. Lexical support remains a separate proxy; use the saved summary and rows for its actual scores. A subsequent request-state isolation fix was verified by regression tests; the live run predates that final isolation change.

`hosted-observation-20261022` is a separate observation of the unchanged Render deployment. All eight responses reported `extractive:offline`, including labels on refusals that do not prove a generator call. It incorrectly refused the expense question and answered dogs-at-work with irrelevant handbook scope. The torrent response was irrelevant. Actual LLM coverage and provider error category cannot be established from that older API. No Render settings, policies, uploads or corpus reset were changed.

No human semantic scores or successful GitHub CI run are claimed for this work. The attempted independent code-review agent was unavailable because of an account usage limit; verification and local review were performed in the main session.

## Human review process

For every row, a named reviewer must read the question, each factual claim, displayed excerpts and original source at the cited section/page. Record:

1. Whether every claim follows from its assigned evidence, including amounts, ranges, exceptions, negation and approval order.
2. Whether the displayed card itself includes the needed evidence/context; opening the full policy must not hide a deficient card.
3. Whether the response answers the whole question and whether a refusal is appropriate.
4. Reviewer name, date and reasons for every failure in `review_sheet.csv`. Leave uncertain assessments blank with notes; do not fill them automatically.

Review both proxy successes and failures. Only calculate human scores after all intended rows have actual human assessments, with denominators and exclusions stated. Re-run when code, prompt, model, configuration or corpus changes. See [README](README.md) for commands and the [Render checklist](docs/render-checklist.md) for hosted diagnosis.
