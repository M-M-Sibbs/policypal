# Evaluation: local-repair-20261022

Target: http://127.0.0.1:5012 (local); evaluator checkout: `bf0654ba299fc3709ce3651974cb6c387aa2b2bd`; dirty: True.
Server revision: unknown; corpus: v1-2a44e4aa53.
Evidence: matched corpus and index configuration. Strict LLM: True.
Observed modes: {"unavailable": 4, "llm": 3, "not_attempted": 1}.
Observed LLM coverage: {"groq:openai/gpt-oss-20b": 3}.
Provider failures: {"malformed_response": 4}.
All quality scores below are automated proxies. Human semantic review is pending.

| Check | Passed / assessed | Percent |
|---|---:|---:|
| behavior_pass | 4/8 | 50.0 |
| automated_pass | 4/8 | 50.0 |
| citation_format_valid | 2/2 | 100.0 |
| snippet_verbatim | 2/2 | 100.0 |
| answer_relevance_proxy | 2/2 | 100.0 |
| evidence_complete_proxy | 2/2 | 100.0 |
| citation_correct_proxy | 2/2 | 100.0 |
| displayed_support_proxy | 1/2 | 50.0 |
| full_passage_support_proxy | 1/2 | 50.0 |
| strict_llm_pass | 4/8 | 50.0 |
| judge_supported | 0/0 | None |

Latency: {"requested": 8, "http_200_count": 4, "p50_ms": 862.8, "p95_ms": 1022.1, "llm_count": 3, "llm_only": {"p50_ms": 872.8, "p95_ms": 1030.9}, "warmup": {"http_status": 200, "generation": {"mode": "llm", "provider": "groq:openai/gpt-oss-20b", "failures": []}, "latency_ms": 3720.4}, "method": "sequential client wall clock after one warmup; no delay included; numpy linear percentile"}

| ID | Status | Mode | Automated pass |
|---|---|---|---|
| Q01 | provider_error | unavailable | False |
| Q03 | provider_error | unavailable | False |
| Q12 | answered | llm | True |
| Q14 | answered | llm | True |
| Q15 | provider_error | unavailable | False |
| Q22 | provider_error | unavailable | False |
| Q24 | insufficient_evidence | llm | True |
| Q28 | out_of_scope | not_attempted | True |
