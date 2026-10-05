## Evaluation run `onnx-groq-final`

- Commit `unknown`, corpus `v1-2a44e4aa53`, 28 questions
- Embeddings `onnx`, generator `groq:openai/gpt-oss-20b`, top_k 8 → top_n 4, threshold 0.3, rerank False
- Groundedness method: lexical-proxy (no JUDGE_PROVIDER set)
- Host: Windows AMD64 / Python 3.11.9

| Metric | Result |
|---|---|
| Groundedness (answered questions) | 73.9% (17/23) |
| Citation accuracy (answered questions) | 100.0% (23/23) |
| Citation validity (all citations) | 100.0% (23/23) |
| Partial match (answerable questions) | 95.7% (22/23) |
| Answer coverage (answerable questions) | 100.0% (23/23) |
| Refusal accuracy (should-refuse questions) | 100.0% (5/5) |
| Latency p50 / p95 (10/10 ok) | 789.9 ms / 954.1 ms |

| ID | Category | Status | Cited | Partial | Cit. correct | Grounded | ms |
|---|---|---|---|---|---|---|---|
| Q01 | direct | answered | POL-02 | yes | yes | yes | 782 |
| Q02 | direct | answered | POL-02 | yes | yes | yes | 982 |
| Q03 | direct | answered | POL-03 | yes | yes | yes | 902 |
| Q04 | direct | answered | POL-03 | yes | yes | yes | 680 |
| Q05 | direct | answered | POL-04 | yes | yes | yes | 745 |
| Q06 | direct | answered | POL-04 | yes | yes | no | 708 |
| Q07 | direct | answered | POL-04 | no | yes | yes | 711 |
| Q08 | direct | answered | POL-05 | yes | yes | yes | 920 |
| Q09 | direct | answered | POL-05 | yes | yes | yes | 851 |
| Q10 | direct | answered | POL-06 | yes | yes | yes | 798 |
| Q11 | direct | answered | POL-06 | yes | yes | yes | 967 |
| Q12 | direct | answered | POL-06 | yes | yes | no | 2993 |
| Q13 | direct | answered | POL-07 | yes | yes | yes | 735 |
| Q14 | direct | answered | POL-07 | yes | yes | yes | 811 |
| Q15 | direct | answered | POL-08 | yes | yes | no | 898 |
| Q16 | direct | answered | POL-09 | yes | yes | yes | 916 |
| Q17 | direct | answered | POL-09 | yes | yes | yes | 775 |
| Q18 | direct | answered | POL-10 | yes | yes | yes | 631 |
| Q19 | direct | answered | POL-11 | yes | yes | no | 673 |
| Q20 | direct | answered | POL-12 | yes | yes | no | 660 |
| Q21 | direct | answered | POL-01 | yes | yes | yes | 786 |
| Q22 | multi_doc | answered | POL-05, POL-08 | yes | yes | no | 836 |
| Q23 | multi_doc | answered | POL-05, POL-07 | yes | yes | yes | 843 |
| Q24 | missing_evidence | insufficient_evidence | - | - | - | - | 826 |
| Q25 | missing_evidence | insufficient_evidence | - | - | - | - | 745 |
| Q26 | out_of_scope | out_of_scope | - | - | - | - | 25 |
| Q27 | out_of_scope | out_of_scope | - | - | - | - | 23 |
| Q28 | adversarial | out_of_scope | - | - | - | - | 23 |
