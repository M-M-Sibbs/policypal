"""Evaluate PolicyPal: groundedness, citation accuracy, refusal behaviour and latency.

    # 1. start the app in another terminal (same settings you want to evaluate)
    gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --threads 4

    # 2. run the evaluation against it
    python -m eval.run --url http://127.0.0.1:5000 --name baseline

Quality is scored on every question in eval/questions.jsonl. Latency is the
client-observed wall-clock time of sequential POST /chat calls (after one
warm-up call) over the first --latency-n questions (default 20).

Groundedness is scored by an LLM judge when JUDGE_PROVIDER / JUDGE_API_KEY /
JUDGE_MODEL are set (use a different model from the generator). Without a judge
a lexical support proxy is used and labelled as such. Every run also writes
review_sheet.csv so a person can record the authoritative human judgement.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.citations import MARKER_RE  # noqa: E402
from app.config import load_settings, set_seeds  # noqa: E402
from app.embeddings import content_tokens  # noqa: E402
from app.generator import OpenAICompatibleClient, ProviderError, split_sentences  # noqa: E402
from app.vectorstore import VectorStore  # noqa: E402

QUESTIONS = ROOT / "eval" / "questions.jsonl"
RESULTS = ROOT / "eval" / "results"
LEXICAL_SUPPORT = 0.8  # share of a sentence's content words that must appear in its cited passages

JUDGE_PROMPT = """You are grading whether an answer is fully supported by evidence passages.
Reply with exactly one word: SUPPORTED if every factual claim in the answer is stated in or
directly implied by the passages, otherwise UNSUPPORTED.

<passages>
{passages}
</passages>

<answer>
{answer}
</answer>"""


def load_questions() -> list[dict]:
    return [
        json.loads(line)
        for line in QUESTIONS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def post(
    url: str,
    question: str,
    timeout: float = 120,
) -> tuple[int, dict, float]:
    started = time.perf_counter()

    try:
        resp = requests.post(
            f"{url}/chat",
            json={"question": question},
            timeout=timeout,
        )

        elapsed = (time.perf_counter() - started) * 1000

        try:
            body = resp.json()
        except ValueError:
            body = {"status": "invalid_json"}

        return resp.status_code, body, elapsed

    except requests.RequestException as exc:
        return (
            0,
            {
                "status": "network_error",
                "message": str(exc),
            },
            (time.perf_counter() - started) * 1000,
        )


def lexical_grounded(
    answer: str,
    passages: list[str],
) -> tuple[bool, float]:
    """Proxy: each answer sentence must have >= 80% of its content words in the cited passages."""

    evidence = set(content_tokens(" ".join(passages)))
    sentences = [
        MARKER_RE.sub("", sentence)
        for sentence in split_sentences(answer)
    ]

    scores = []

    for sentence in sentences:
        tokens = content_tokens(sentence)

        if tokens:
            scores.append(
                sum(token in evidence for token in tokens) / len(tokens)
            )

    if not scores:
        return False, 0.0

    return (
        min(scores) >= LEXICAL_SUPPORT,
        round(min(scores), 3),
    )


def build_judge():
    provider = os.getenv("JUDGE_PROVIDER", "").lower()

    if not provider:
        return None

    return OpenAICompatibleClient(
        provider,
        os.getenv("JUDGE_API_KEY", ""),
        os.getenv("JUDGE_MODEL", ""),
        os.getenv("JUDGE_BASE_URL", ""),
        timeout=60,
        temperature=0.0,
        max_tokens=5,
        seed=42,
    )


def judge_grounded(
    judge,
    answer: str,
    passages: list[str],
) -> bool | None:
    prompt = JUDGE_PROMPT.format(
        passages="\n\n".join(passages),
        answer=MARKER_RE.sub("", answer),
    )

    try:
        verdict = judge.complete(
            [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        ).strip().upper()

    except ProviderError:
        return None

    return verdict.startswith("SUPPORTED")


def git_commit() -> str:
    try:
        return subprocess.check_output(
            [
                "git",
                "rev-parse",
                "--short",
                "HEAD",
            ],
            cwd=ROOT,
            text=True,
        ).strip()

    except Exception:
        return "unknown"


def percentile(
    values: list[float],
    q: float,
) -> float:
    return float(
        np.percentile(
            values,
            q,
            method="linear",
        )
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--url",
        default="http://127.0.0.1:5000",
    )

    parser.add_argument(
        "--name",
        default=datetime.now(timezone.utc).strftime(
            "run-%Y%m%d-%H%M%S"
        ),
    )

    parser.add_argument(
        "--latency-n",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--delay-s",
        type=float,
        default=0.0,
        help="Seconds to wait between quality-evaluation requests.",
    )

    args = parser.parse_args(argv)

    settings = load_settings()
    set_seeds(settings.seed)

    url = args.url.rstrip("/")

    health = requests.get(
        f"{url}/health",
        timeout=30,
    ).json()

    if not health.get("index_ready"):
        print(
            f"index not ready: {health}"
        )
        return 1

    # chunk text lookup for citation validity / grounding checks
    # (same index the server uses)
    chunk_text = {
        chunk.chunk_id: chunk.text
        for chunk in VectorStore(
            settings.chroma_dir,
            settings.collection_name,
        ).get_all()
    }

    judge = build_judge()
    questions = load_questions()

    # ---- warm-up (excluded from latency) ----

    warm_status, _, warm_ms = post(
        url,
        "How many PTO days do I get per year?",
    )

    rows = []

    for index, q in enumerate(questions):
        code, body, elapsed = post(
            url,
            q["question"],
        )

        citations = body.get(
            "citations",
            [],
        ) or []

        answer = body.get(
            "answer",
            "",
        )

        refused = (
            bool(body.get("refused"))
            or body.get("status")
            in {
                "out_of_scope",
                "insufficient_evidence",
            }
        )

        answered = (
            body.get("status")
            == "answered"
        )

        cited_docs = sorted(
            {
                citation["document_id"]
                for citation in citations
            }
        )

        passages = [
            chunk_text.get(
                citation["chunk_id"],
                "",
            )
            for citation in citations
        ]

        valid = [
            bool(
                citation["chunk_id"]
                in chunk_text
                and citation["snippet"].rstrip("…")
                in chunk_text[citation["chunk_id"]]
            )
            for citation in citations
        ]

        facts = [
            fact.lower()
            for fact in q["gold_facts"]
        ]

        fact_in_answer = (
            any(
                fact in answer.lower()
                for fact in facts
            )
            if facts
            else None
        )

        fact_in_citation = (
            any(
                fact in passage.lower()
                for fact in facts
                for passage in passages
            )
            if facts
            else None
        )

        cite_correct = None

        if (
            answered
            and not q["should_refuse"]
        ):
            cite_correct = (
                bool(citations)
                and set(cited_docs)
                <= set(q["gold_doc_ids"])
                and bool(fact_in_citation)
            )

        grounded = None
        lexical_score = None
        method = None

        if answered:
            grounded, lexical_score = lexical_grounded(
                answer,
                passages,
            )

            method = "lexical-proxy"

            if judge is not None:
                verdict = judge_grounded(
                    judge,
                    answer,
                    passages,
                )

                if verdict is not None:
                    grounded = verdict
                    method = (
                        f"llm-judge:{judge.label}"
                    )

        rows.append(
            {
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "should_refuse": q["should_refuse"],
                "http_status": code,
                "status": body.get("status"),
                "refused": refused,
                "behavior_pass": (
                    refused
                    == q["should_refuse"]
                    and code == 200
                ),
                "answer": answer,
                "gold_answer": q["gold_answer"],
                "gold_doc_ids": q["gold_doc_ids"],
                "cited_docs": cited_docs,
                "citations": citations,
                "citation_valid": (
                    all(valid)
                    if citations
                    else None
                ),
                "partial_match": (
                    fact_in_answer
                    if (
                        answered
                        and facts
                    )
                    else (
                        False
                        if facts
                        else None
                    )
                ),
                "citation_correct": cite_correct,
                "grounded": grounded,
                "lexical_support": lexical_score,
                "grounding_method": method,
                "provider": body.get("provider"),
                "best_similarity": (
                    body.get("retrieval")
                    or {}
                ).get("best_similarity"),
                "latency_ms": round(
                    elapsed,
                    1,
                ),
                "server_latency_ms": body.get(
                    "latency_ms"
                ),
            }
        )

        print(
            f"{q['id']} "
            f"{body.get('status'):<22} "
            f"{elapsed:7.0f} ms  "
            f"{answer[:80]!r}"
        )

        # Throttle quality-evaluation requests so API-backed generators
        # can remain within provider rate limits.
        #
        # Do not sleep after the final question.
        if (
            args.delay_s > 0
            and index < len(questions) - 1
        ):
            time.sleep(args.delay_s)

    # ---- metrics ----

    def ratio(values):
        vals = [
            value
            for value in values
            if value is not None
        ]

        return (
            sum(vals),
            len(vals),
            (
                round(
                    100 * sum(vals) / len(vals),
                    1,
                )
                if vals
                else None
            ),
        )

    answerable = [
        row
        for row in rows
        if not row["should_refuse"]
    ]

    answered_rows = [
        row
        for row in answerable
        if row["status"] == "answered"
    ]

    boundary = [
        row
        for row in rows
        if row["should_refuse"]
    ]

    latency_rows = rows[
        : args.latency_n
    ]

    ok_lat = [
        row["latency_ms"]
        for row in latency_rows
        if row["http_status"] == 200
    ]

    failures = [
        row["id"]
        for row in latency_rows
        if row["http_status"] != 200
    ]

    metrics = {
        "groundedness": ratio(
            [
                row["grounded"]
                for row in answered_rows
            ]
        ),
        "citation_accuracy": ratio(
            [
                row["citation_correct"]
                for row in answered_rows
            ]
        ),
        "citation_validity": ratio(
            [
                row["citation_valid"]
                for row in rows
                if row["citation_valid"]
                is not None
            ]
        ),
        "partial_match": ratio(
            [
                bool(row["partial_match"])
                for row in answerable
            ]
        ),
        "answer_coverage": ratio(
            [
                row["status"]
                == "answered"
                for row in answerable
            ]
        ),
        "refusal_accuracy": ratio(
            [
                row["behavior_pass"]
                for row in boundary
            ]
        ),
        "behavior_accuracy_all": ratio(
            [
                row["behavior_pass"]
                for row in rows
            ]
        ),
    }

    latency = {
        "n_requests": len(
            latency_rows
        ),
        "n_successful": len(
            ok_lat
        ),
        "failures": failures,
        "p50_ms": (
            round(
                percentile(
                    ok_lat,
                    50,
                ),
                1,
            )
            if ok_lat
            else None
        ),
        "p95_ms": (
            round(
                percentile(
                    ok_lat,
                    95,
                ),
                1,
            )
            if ok_lat
            else None
        ),
        "mean_ms": (
            round(
                statistics.mean(
                    ok_lat
                ),
                1,
            )
            if ok_lat
            else None
        ),
        "max_ms": (
            round(
                max(ok_lat),
                1,
            )
            if ok_lat
            else None
        ),
        "warmup_ms": round(
            warm_ms,
            1,
        ),
        "warmup_status": warm_status,
        "method": (
            "client-observed wall clock, sequential, "
            "after 1 warm-up call; numpy linear percentile"
        ),
    }

    summary = {
        "run": args.name,
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(
            timespec="seconds"
        ),
        "commit": git_commit(),
        "url": url,
        "health": health,
        "settings": {
            "embed_backend": health.get(
                "embed_backend"
            ),
            "llm_provider": health.get(
                "llm_provider"
            ),
            "provider_label": (
                rows[0]["provider"]
                if rows
                else None
            ),
            "top_k": settings.top_k,
            "top_n": settings.top_n,
            "score_threshold": settings.score_threshold,
            "rerank": settings.rerank,
            "chunk_tokens": settings.chunk_tokens,
            "chunk_overlap": settings.chunk_overlap,
            "seed": settings.seed,
            "delay_s": args.delay_s,
        },
        "grounding_method": (
            "llm-judge"
            if judge
            else "lexical-proxy (no JUDGE_PROVIDER set)"
        ),
        "host": (
            f"{platform.system()} "
            f"{platform.machine()} / "
            f"Python {platform.python_version()}"
        ),
        "n_questions": len(rows),
        "metrics": {
            key: {
                "numerator": value[0],
                "denominator": value[1],
                "percent": value[2],
            }
            for key, value
            in metrics.items()
        },
        "latency": latency,
    }

    out = RESULTS / args.name

    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        out / "results.jsonl",
        "w",
        encoding="utf-8",
    ) as f:
        for row in rows:
            f.write(
                json.dumps(row)
                + "\n"
            )

    (
        out
        / "summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with open(
        out / "latency.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)

        writer.writerow(
            [
                "id",
                "http_status",
                "status",
                "client_latency_ms",
                "server_latency_ms",
            ]
        )

        for row in latency_rows:
            writer.writerow(
                [
                    row["id"],
                    row["http_status"],
                    row["status"],
                    row["latency_ms"],
                    row["server_latency_ms"],
                ]
            )

    with open(
        out / "review_sheet.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)

        writer.writerow(
            [
                "id",
                "question",
                "answer",
                "cited_docs",
                "gold_doc_ids",
                "auto_grounded",
                "auto_citation_correct",
                "human_grounded (Y/N)",
                "human_citation_correct (Y/N)",
                "reviewer",
                "notes",
            ]
        )

        for row in rows:
            writer.writerow(
                [
                    row["id"],
                    row["question"],
                    row["answer"],
                    ";".join(
                        row["cited_docs"]
                    ),
                    ";".join(
                        row["gold_doc_ids"]
                    ),
                    row["grounded"],
                    row["citation_correct"],
                    "",
                    "",
                    "",
                    "",
                ]
            )

    (
        out
        / "summary.md"
    ).write_text(
        render_markdown(
            summary,
            rows,
        ),
        encoding="utf-8",
    )

    print(
        "\n"
        + render_markdown(
            summary,
            rows,
        )
    )

    print(
        f"results written to "
        f"{out.relative_to(ROOT)}"
    )

    return 0


def render_markdown(
    summary: dict,
    rows: list[dict],
) -> str:
    metrics = summary["metrics"]
    latency = summary["latency"]

    def cell(key):
        value = metrics[key]

        return (
            f"{value['percent']}% "
            f"({value['numerator']}/"
            f"{value['denominator']})"
            if value["percent"]
            is not None
            else "n/a"
        )

    lines = [
        f"## Evaluation run `{summary['run']}`",
        "",
        (
            f"- Commit `{summary['commit']}`, "
            f"corpus "
            f"`{summary['health'].get('corpus_version')}`, "
            f"{summary['n_questions']} questions"
        ),
        (
            f"- Embeddings "
            f"`{summary['settings']['embed_backend']}`, "
            f"generator "
            f"`{summary['settings']['provider_label']}`, "
            f"top_k "
            f"{summary['settings']['top_k']} "
            f"→ top_n "
            f"{summary['settings']['top_n']}, "
            f"threshold "
            f"{summary['settings']['score_threshold']}, "
            f"rerank "
            f"{summary['settings']['rerank']}"
        ),
        (
            f"- Groundedness method: "
            f"{summary['grounding_method']}"
        ),
        (
            f"- Host: "
            f"{summary['host']}"
        ),
        "",
        "| Metric | Result |",
        "|---|---|",
        (
            "| Groundedness "
            "(answered questions) | "
            f"{cell('groundedness')} |"
        ),
        (
            "| Citation accuracy "
            "(answered questions) | "
            f"{cell('citation_accuracy')} |"
        ),
        (
            "| Citation validity "
            "(all citations) | "
            f"{cell('citation_validity')} |"
        ),
        (
            "| Partial match "
            "(answerable questions) | "
            f"{cell('partial_match')} |"
        ),
        (
            "| Answer coverage "
            "(answerable questions) | "
            f"{cell('answer_coverage')} |"
        ),
        (
            "| Refusal accuracy "
            "(should-refuse questions) | "
            f"{cell('refusal_accuracy')} |"
        ),
        (
            "| Latency p50 / p95 "
            f"({latency['n_successful']}/"
            f"{latency['n_requests']} ok) | "
            f"{latency['p50_ms']} ms / "
            f"{latency['p95_ms']} ms |"
        ),
        "",
        (
            "| ID | Category | Status | "
            "Cited | Partial | Cit. correct | "
            "Grounded | ms |"
        ),
        (
            "|---|---|---|---|---|---|---|---|"
        ),
    ]

    for row in rows:
        lines.append(
            f"| {row['id']} | "
            f"{row['category']} | "
            f"{row['status']} | "
            f"{', '.join(row['cited_docs']) or '-'} | "
            f"{_yn(row['partial_match'])} | "
            f"{_yn(row['citation_correct'])} | "
            f"{_yn(row['grounded'])} | "
            f"{row['latency_ms']:.0f} |"
        )

    return "\n".join(lines) + "\n"


def _yn(value):
    return (
        "-"
        if value is None
        else (
            "yes"
            if value
            else "no"
        )
    )


if __name__ == "__main__":
    sys.exit(main())