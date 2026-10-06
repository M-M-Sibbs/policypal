## Evaluation run `render-latency`

- Commit `9fe45f7`, corpus `v1-2a44e4aa53`, 28 questions
- Embeddings `onnx`, generator `extractive:offline`, top_k 8 → top_n 4, threshold 0.35, rerank True
- Groundedness method: lexical-proxy (no JUDGE_PROVIDER set)
- Host: Windows AMD64 / Python 3.13.14

| Metric | Result |
|---|---|
| Groundedness (answered questions) | 100.0% (6/6) |
| Citation accuracy (answered questions) | 83.3% (5/6) |
| Citation validity (all citations) | 100.0% (6/6) |
| Partial match (answerable questions) | 21.7% (5/23) |
| Answer coverage (answerable questions) | 26.1% (6/23) |
| Refusal accuracy (should-refuse questions) | 0.0% (0/5) |
| Latency p50 / p95 (6/20 ok) | 8251.9 ms / 12084.7 ms |

| ID | Category | Status | Cited | Partial | Cit. correct | Grounded | ms |
|---|---|---|---|---|---|---|---|
| Q01 | direct | answered | POL-02 | yes | yes | yes | 4474 |
| Q02 | direct | answered | POL-02 | yes | yes | yes | 6280 |
| Q03 | direct | answered | POL-03 | no | no | yes | 9397 |
| Q04 | direct | answered | POL-03 | yes | yes | yes | 8216 |
| Q05 | direct | answered | POL-04 | yes | yes | yes | 8288 |
| Q06 | direct | answered | POL-04 | yes | yes | yes | 12980 |
| Q07 | direct | network_error | - | no | - | - | 125754 |
| Q08 | direct | network_error | - | no | - | - | 17 |
| Q09 | direct | network_error | - | no | - | - | 7 |
| Q10 | direct | network_error | - | no | - | - | 4 |
| Q11 | direct | network_error | - | no | - | - | 6 |
| Q12 | direct | network_error | - | no | - | - | 8 |
| Q13 | direct | network_error | - | no | - | - | 39 |
| Q14 | direct | network_error | - | no | - | - | 4 |
| Q15 | direct | network_error | - | no | - | - | 7 |
| Q16 | direct | network_error | - | no | - | - | 4 |
| Q17 | direct | network_error | - | no | - | - | 6 |
| Q18 | direct | network_error | - | no | - | - | 6 |
| Q19 | direct | network_error | - | no | - | - | 11 |
| Q20 | direct | network_error | - | no | - | - | 151 |
| Q21 | direct | network_error | - | no | - | - | 8 |
| Q22 | multi_doc | network_error | - | no | - | - | 6 |
| Q23 | multi_doc | network_error | - | no | - | - | 8 |
| Q24 | missing_evidence | network_error | - | - | - | - | 7 |
| Q25 | missing_evidence | network_error | - | - | - | - | 7 |
| Q26 | out_of_scope | network_error | - | - | - | - | 3 |
| Q27 | out_of_scope | network_error | - | - | - | - | 1 |
| Q28 | adversarial | network_error | - | - | - | - | 7 |
