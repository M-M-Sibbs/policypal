"""Suggest a SCORE_THRESHOLD for the configured embedding backend.

    python scripts/calibrate_threshold.py

For each evaluation question it records the best cosine similarity between the
question and the index. The threshold should sit between answerable questions
(which must pass) and out-of-scope questions (which should be refused before
the LLM is called). Missing-evidence questions are listed but not used: they
are on-topic, so they are left to the model's evidence check.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.embeddings import build_embedder  # noqa: E402
from app.retriever import Retriever  # noqa: E402
from app.vectorstore import VectorStore  # noqa: E402


def main() -> int:
    s = load_settings().with_overrides(rerank=False)
    retriever = Retriever(s, VectorStore(s.chroma_dir, s.collection_name), build_embedder(s.embed_backend, s.embed_model))
    questions = [json.loads(l) for l in (ROOT / "eval" / "questions.jsonl").read_text().splitlines() if l.strip()]
    pos, neg = [], []
    print(f"{'id':<5}{'category':<18}{'best_sim':>9}  question")
    for q in questions:
        best = retriever.retrieve(q["question"]).best_similarity
        print(f"{q['id']:<5}{q['category']:<18}{best:9.3f}  {q['question'][:70]}")
        if not q["should_refuse"]:
            pos.append(best)
        elif q["category"] in {"out_of_scope", "adversarial"}:
            neg.append(best)
    lowest_pos, highest_neg = min(pos), max(neg)
    print(f"\nanswerable: min {lowest_pos:.3f}   out-of-scope: max {highest_neg:.3f}")
    if highest_neg < lowest_pos:
        suggestion = round((lowest_pos + highest_neg) / 2, 3)
        print(f"Separable. Suggested SCORE_THRESHOLD={suggestion} (midpoint) for EMBED_BACKEND={s.embed_backend}")
    else:
        best_t, best_acc = None, -1.0
        for t in sorted(set(pos + neg)):
            acc = (sum(p >= t for p in pos) + sum(n < t for n in neg)) / (len(pos) + len(neg))
            if acc > best_acc:
                best_t, best_acc = t, acc
        print(f"Not separable. Best single threshold {best_t:.3f} classifies {best_acc:.0%} correctly; "
              "rely on the model's evidence check for the rest.")
    print(f"Current SCORE_THRESHOLD={s.score_threshold}")
    print("Note: these questions are also the evaluation set; confirm on fresh questions to avoid overfitting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
