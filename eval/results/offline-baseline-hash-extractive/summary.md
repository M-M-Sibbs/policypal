## Evaluation run `offline-baseline-hash-extractive`

- Commit `unknown`, corpus `v1-2a44e4aa53`, 28 questions
- Embeddings `hash`, generator `extractive:offline`, top_k 8 → top_n 4, threshold 0.12, rerank False
- Groundedness method: lexical-proxy (no JUDGE_PROVIDER set)
- Host: Linux x86_64 / Python 3.11.15

| Metric | Result |
|---|---|
| Groundedness (answered questions) | 100.0% (22/22) |
| Citation accuracy (answered questions) | 72.7% (16/22) |
| Citation validity (all citations) | 100.0% (23/23) |
| Partial match (answerable questions) | 73.9% (17/23) |
| Answer coverage (answerable questions) | 95.7% (22/23) |
| Refusal accuracy (should-refuse questions) | 80.0% (4/5) |
| Latency p50 / p95 (20/20 ok) | 6.5 ms / 7.6 ms |

| ID | Category | Status | Cited | Partial | Cit. correct | Grounded | ms |
|---|---|---|---|---|---|---|---|
| Q01 | direct | answered | POL-02 | yes | yes | yes | 9 |
| Q02 | direct | answered | POL-02 | yes | yes | yes | 7 |
| Q03 | direct | answered | POL-03 | no | no | yes | 6 |
| Q04 | direct | answered | POL-03 | yes | yes | yes | 7 |
| Q05 | direct | answered | POL-04 | yes | yes | yes | 7 |
| Q06 | direct | answered | POL-04 | yes | yes | yes | 6 |
| Q07 | direct | answered | POL-04 | yes | yes | yes | 7 |
| Q08 | direct | answered | POL-01, POL-05 | yes | no | yes | 7 |
| Q09 | direct | answered | POL-05 | yes | yes | yes | 6 |
| Q10 | direct | answered | POL-06 | yes | yes | yes | 6 |
| Q11 | direct | answered | POL-06 | yes | yes | yes | 6 |
| Q12 | direct | insufficient_evidence | - | no | - | - | 5 |
| Q13 | direct | answered | POL-07 | yes | yes | yes | 6 |
| Q14 | direct | answered | POL-07, POL-08 | yes | no | yes | 5 |
| Q15 | direct | answered | POL-07 | no | no | yes | 6 |
| Q16 | direct | answered | POL-09 | no | no | yes | 6 |
| Q17 | direct | answered | POL-09 | no | yes | yes | 7 |
| Q18 | direct | answered | POL-10 | yes | yes | yes | 7 |
| Q19 | direct | answered | POL-11 | no | no | yes | 6 |
| Q20 | direct | answered | POL-12 | yes | yes | yes | 8 |
| Q21 | direct | answered | POL-01 | yes | yes | yes | 15 |
| Q22 | multi_doc | answered | POL-05 | yes | yes | yes | 6 |
| Q23 | multi_doc | answered | POL-05, POL-07 | yes | yes | yes | 5 |
| Q24 | missing_evidence | answered | POL-06 | - | - | yes | 8 |
| Q25 | missing_evidence | insufficient_evidence | - | - | - | - | 6 |
| Q26 | out_of_scope | out_of_scope | - | - | - | - | 6 |
| Q27 | out_of_scope | insufficient_evidence | - | - | - | - | 6 |
| Q28 | adversarial | out_of_scope | - | - | - | - | 6 |
