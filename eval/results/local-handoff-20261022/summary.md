# Evaluation: local-handoff-20261022

Target: http://127.0.0.1:5012 (local); evaluator checkout: `bf0654ba299fc3709ce3651974cb6c387aa2b2bd`; dirty: True.
Server revision: unknown; corpus: v1-2a44e4aa53.
Evidence: matched corpus and index configuration. Strict LLM: True.
Observed modes: {"llm": 7, "not_attempted": 1}.
Observed LLM coverage: {"groq:openai/gpt-oss-20b": 7}.
Provider failures: {}.
All quality scores below are automated proxies. Human semantic review is pending.

| Check | Passed / assessed | Percent |
|---|---:|---:|
| behavior_pass | 8/8 | 100.0 |
| automated_pass | 8/8 | 100.0 |
| citation_format_valid | 6/6 | 100.0 |
| snippet_verbatim | 6/6 | 100.0 |
| answer_relevance_proxy | 6/6 | 100.0 |
| evidence_complete_proxy | 6/6 | 100.0 |
| citation_correct_proxy | 6/6 | 100.0 |
| displayed_support_proxy | 4/6 | 66.7 |
| full_passage_support_proxy | 4/6 | 66.7 |
| strict_llm_pass | 8/8 | 100.0 |
| judge_supported | 0/0 | None |

Latency: {"requested": 8, "http_200_count": 8, "p50_ms": 797.9, "p95_ms": 2010.1, "llm_count": 7, "llm_only": {"p50_ms": 871.3, "p95_ms": 2024.5}, "warmup": {"http_status": 200, "generation": {"mode": "llm", "provider": "groq:openai/gpt-oss-20b", "failures": []}, "latency_ms": 1717.3}, "method": "sequential client wall clock after one warmup; no delay included; numpy linear percentile"}

| ID | Status | Mode | Automated pass |
|---|---|---|---|
| Q01 | answered | llm | True |
| Q03 | answered | llm | True |
| Q12 | answered | llm | True |
| Q14 | answered | llm | True |
| Q15 | answered | llm | True |
| Q22 | answered | llm | True |
| Q24 | insufficient_evidence | llm | True |
| Q28 | out_of_scope | not_attempted | True |
